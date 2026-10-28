#include "app.hpp"
#include "kernels.hpp"
#include "platform.hpp"
#include "queue.hpp"
#include <array>
#include <atomic>
#include <cmath>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

namespace edge {
namespace fs = std::filesystem;
struct Options {
    fs::path input, out;
    std::string allocation="pool", traversal="row", io="file", profile="source";
    std::size_t frames=0, queue=5, slots=34, capture=0, edge_threshold=80;
    double rate=0;
};
static std::size_t number(const std::string& s) {
    if (s.empty() || s.find_first_not_of("0123456789")!=std::string::npos)
        throw std::invalid_argument("expected nonnegative integer: "+s);
    const auto n=std::stoull(s);
    if (n>std::numeric_limits<std::size_t>::max()) throw std::out_of_range("integer too large");
    return static_cast<std::size_t>(n);
}
static Options parse(int argc, char** argv) {
    Options o; std::set<std::string> seen;
    for (int i=1;i<argc;++i) {
        const std::string k=argv[i];
        if (!seen.insert(k).second) throw std::invalid_argument("duplicate option: "+k);
        if (i+1==argc) throw std::invalid_argument("missing value for "+k);
        const std::string v=argv[++i];
        if(k=="--input") o.input=v;
        else if(k=="--out") o.out=v;
        else if(k=="--allocation") o.allocation=v;
        else if(k=="--traversal") o.traversal=v;
        else if(k=="--io") o.io=v;
        else if(k=="--profile") o.profile=v;
        else if(k=="--edge-threshold") o.edge_threshold=number(v);
        else if(k=="--frames") o.frames=number(v);
        else if(k=="--queue") o.queue=number(v);
        else if(k=="--slots") o.slots=number(v);
        else if(k=="--capture") o.capture=number(v);
        else if(k=="--rate") {
            std::size_t end=0; o.rate=std::stod(v,&end);
            if(end!=v.size() || !std::isfinite(o.rate) || o.rate<0 || o.rate>1000)
                throw std::invalid_argument("rate must be finite and in [0,1000]");
        } else throw std::invalid_argument("unknown option: "+k);
    }
    if(o.input.empty() || o.out.empty()) throw std::invalid_argument("--input and --out are required");
    if(o.allocation!="pool" && o.allocation!="dynamic") throw std::invalid_argument("allocation: pool|dynamic");
    if(o.traversal!="row" && o.traversal!="column") throw std::invalid_argument("traversal: row|column");
    if(o.io!="file" && o.io!="ram") throw std::invalid_argument("io: file|ram");
    if(o.profile!="source" && o.profile!="legacy") throw std::invalid_argument("profile: source|legacy");
    if(o.edge_threshold>1020) throw std::invalid_argument("edge-threshold: 0..1020 in raw Sobel units");
    if(o.queue<1 || o.queue>1024 || o.slots<1 || o.slots>4096 || o.frames>1000000)
        throw std::invalid_argument("queue 1..1024, slots 1..4096, frames 0..1000000 required");
    return o;
}

class Source {
    std::ifstream stream_;
    std::vector<std::uint8_t> ram_;
public:
    std::size_t width=0,height=0,count=0,bytes=0;
    std::uintmax_t file_bytes=0;
    explicit Source(const Options& o):stream_(o.input,std::ios::binary) {
        if(!stream_) throw std::runtime_error("cannot open input: "+o.input.string());
        std::array<unsigned char,20> h{};
        stream_.read(reinterpret_cast<char*>(h.data()),20);
        if(!stream_ || std::memcmp(h.data(),"EPRAW01\n",8)!=0)
            throw std::runtime_error("invalid EPRAW01 header; prepare the dataset first");
        auto u32=[&](int p) {return std::uint32_t(h[p]) | (std::uint32_t(h[p+1])<<8) |
                                   (std::uint32_t(h[p+2])<<16) | (std::uint32_t(h[p+3])<<24);};
        width=u32(8); height=u32(12); count=u32(16);
        if(width<3 || height<3 || width>8192 || height>8192 || !count || count>1000000)
            throw std::runtime_error("invalid dataset dimensions/count");
        bytes=width*height*3;
        file_bytes=fs::file_size(o.input);
        if(file_bytes!=20ULL+static_cast<std::uint64_t>(bytes)*count)
            throw std::runtime_error("input length mismatch (truncated or extra data)");
        if(o.io=="ram") {
            if(file_bytes-20>1024ULL*1024*1024)
                throw std::runtime_error("RAM replay limited to 1 GiB; prepare a smaller subset or use --io file");
            ram_.resize(bytes*count);
            stream_.read(reinterpret_cast<char*>(ram_.data()),static_cast<std::streamsize>(ram_.size()));
            if(!stream_) throw std::runtime_error("RAM preload failed");
        }
    }
    void fetch(std::size_t id,std::uint8_t* dst) {
        const auto offset=(id%count)*bytes;
        if(!ram_.empty()) { std::memcpy(dst,ram_.data()+offset,bytes); return; }
        stream_.seekg(static_cast<std::streamoff>(20+offset));
        stream_.read(reinterpret_cast<char*>(dst),static_cast<std::streamsize>(bytes));
        if(!stream_) throw std::runtime_error("frame read failed at replay frame "+std::to_string(id));
    }
};
struct Record {
    std::size_t id=0, slot_id=0;
    double request=0, admit=0, done=0, scheduled=0;
    std::array<double,4> begin{}, end{};
    std::uint64_t sum=0, weighted=0;
};
struct Slot {
    std::unique_ptr<std::uint8_t[]> rgb, gray, edges;
    Record m;
    void allocate(std::size_t n) {
        // Uninitialized storage: every output byte is overwritten by the kernels.
        rgb.reset(new std::uint8_t[3*n]); gray.reset(new std::uint8_t[n]); edges.reset(new std::uint8_t[n]);
    }
    void release() { rgb.reset(); gray.reset(); edges.reset(); }
};
struct Worker {
    std::string thread_id;
    Wait input, output;
    double cpu=0, service=0, pace_sleep=0;
};
static double quantile(std::vector<double> v,double p) {
    std::sort(v.begin(),v.end());
    const double x=p*static_cast<double>(v.size()-1);
    const auto lo=static_cast<std::size_t>(x);
    return v[lo]+(v[std::min(lo+1,v.size()-1)]-v[lo])*(x-static_cast<double>(lo));
}
static void json_number(std::ostream& out,double x) { if(std::isfinite(x)) out<<x; else out<<"null"; }

int run(int argc, char** argv, bool pipeline) {
  try {
    if(argc==2 && std::string(argv[1])=="--help") {
        std::cout << "Usage: edge_" << (pipeline?"pipeline":"seq")
          << " --input FILE.epraw --out NEW_DIRECTORY [options]\n"
          << "--frames N (0=source count, repeats input when N>count)\n"
          << "--allocation pool|dynamic --traversal row|column --io file|ram\n"
          << "--profile source|legacy (default source: Chen-2024 Sec. 4.4; US6553131B1 Fig. 1 block 16)\n"
          << "--edge-threshold N (source only; default 80, project-selected raw Sobel units)\n"
          << "--queue N (default 5) --slots N (default 34, pipeline only)\n"
          << "--rate FPS (0=unpaced; paced replay blocks, never drops)\n"
          << "--capture N (first N gray, final edge and source-profile pre-closing binary frames, demo/correctness only; adds copying)\n";
        return 0;
    }
    const auto setup_start=Clock::now();
    auto o=parse(argc,argv); Source source(o);
    if(!o.frames) o.frames=source.count;
    if(o.capture>o.frames) throw std::invalid_argument("capture cannot exceed frames");
    if(fs::exists(o.out)) throw std::runtime_error("output directory already exists; choose a fresh --out");
    const std::size_t pixels=source.width*source.height, slots_n=pipeline?o.slots:1;
    const std::uint64_t frame_bound=5ULL*pixels*slots_n+pixels;
    const std::uint64_t capture_plane_bytes=static_cast<std::uint64_t>(o.capture)*pixels;
    const std::uint64_t capture_bytes=capture_plane_bytes*(o.profile=="source"?3:2);
    if(capture_bytes>512ULL*1024*1024 || frame_bound+capture_bytes+o.frames*sizeof(Record)>2ULL*1024*1024*1024)
        throw std::runtime_error("requested working buffers/records exceed project memory guard");
    std::vector<Slot> slots(slots_n);
    if(o.allocation=="pool") for(auto& s:slots) s.allocate(pixels);
    std::unique_ptr<std::uint8_t[]> output(new std::uint8_t[pixels]);
    std::unique_ptr<std::uint8_t[]> captured;
    if(capture_bytes) captured.reset(new std::uint8_t[static_cast<std::size_t>(capture_bytes)]);
    std::vector<Record> records(o.frames);
    std::array<Worker,4> workers{};
    Queue free_slots(slots_n), q1(o.queue), q2(o.queue), q3(o.queue);
    for(std::size_t i=0;i<slots_n;++i) free_slots.seed(i);
    std::atomic<bool> cancelled{false};
    std::exception_ptr failure;
    std::mutex error_mutex,gate_mutex;
    std::condition_variable gate_cv;
    bool gate_open=false;
    Time start;
    auto stamp=[&] {return seconds(start,Clock::now());};
    auto cancel=[&] {
        cancelled=true; free_slots.close(); q1.close(); q2.close(); q3.close(); gate_cv.notify_all();
    };
    auto pace=[&](std::size_t id) {
        if(o.rate==0) return;
        const auto target=start+std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(static_cast<double>(id)/o.rate));
        const auto before=Clock::now();
        // Cancellation wakes paced producers as well as queue waiters.
        std::unique_lock lock(gate_mutex);
        gate_cv.wait_until(lock,target,[&]{return cancelled.load();});
        workers[0].pace_sleep+=seconds(before,Clock::now());
    };
    auto fetch=[&](Slot& s,std::size_t id,double request) {
        s.m={}; s.m.id=id; s.m.slot_id=static_cast<std::size_t>(&s-slots.data()); s.m.request=request; s.m.admit=stamp();
        s.m.scheduled=o.rate>0?static_cast<double>(id)/o.rate:s.m.admit;
        s.m.begin[0]=s.m.admit;
        if(o.allocation=="dynamic") s.allocate(pixels);
        source.fetch(id,s.rgb.get());
        s.m.end[0]=stamp();
        workers[0].service+=s.m.end[0]-s.m.begin[0];
    };
    auto gray=[&](Slot& s) {
        s.m.begin[1]=stamp();
        gray_contrast(s.rgb.get(),s.gray.get(),source.width,source.height,o.traversal=="column");
        s.m.end[1]=stamp(); workers[1].service+=s.m.end[1]-s.m.begin[1];
    };
    auto edges=[&](Slot& s) {
        s.m.begin[2]=stamp();
        if(o.profile=="source") {
            vertical_sobel(s.gray.get(),s.edges.get(),source.width,source.height,o.traversal=="column",static_cast<int>(o.edge_threshold));
            if(s.m.id<o.capture)
                std::memcpy(captured.get()+2*capture_plane_bytes+s.m.id*pixels,s.edges.get(),pixels);
            close_binary(s.edges.get(),s.rgb.get(),source.width,source.height,o.traversal=="column");
        } else sobel(s.gray.get(),s.edges.get(),source.width,source.height,o.traversal=="column");
        s.m.end[2]=stamp(); workers[2].service+=s.m.end[2]-s.m.begin[2];
    };
    std::size_t completed=0;
    auto sink=[&](Slot& s) {
        if(s.m.id!=completed) throw std::logic_error("frame order/identity violation");
        s.m.begin[3]=stamp();
        std::memcpy(output.get(),s.edges.get(),pixels);
        const auto fp=fingerprint(output.get(),pixels); s.m.sum=fp.first; s.m.weighted=fp.second;
        if(s.m.id<o.capture) {
            std::memcpy(captured.get()+s.m.id*pixels,output.get(),pixels);
            std::memcpy(captured.get()+(o.capture+s.m.id)*pixels,s.gray.get(),pixels);
        }
        if(o.allocation=="dynamic") s.release();
        s.m.end[3]=stamp(); s.m.done=s.m.end[3];
        workers[3].service+=s.m.end[3]-s.m.begin[3];
        records[s.m.id]=s.m; ++completed;
    };
    std::vector<std::thread> threads; threads.reserve(4);
    auto launch=[&](std::size_t idx,auto fn) {
        threads.emplace_back([&,idx,fn] {
            { std::unique_lock lock(gate_mutex); gate_cv.wait(lock,[&]{return gate_open || cancelled.load();}); }
            if(cancelled) return;
            std::ostringstream tid; tid<<std::this_thread::get_id(); workers[idx].thread_id=tid.str();
            const double c=cpu_seconds(true);
            try { fn(); }
            catch(...) {
                { std::lock_guard lock(error_mutex); if(!failure) failure=std::current_exception(); }
                cancel();
            }
            workers[idx].cpu=cpu_seconds(true)-c;
        });
    };
    if(pipeline) {
        try {
            launch(0,[&] {
                for(std::size_t id=0;id<o.frames && !cancelled;++id) {
                    pace(id); const double request=stamp(); std::size_t slot=0;
                    if(cancelled || !free_slots.pop(slot,workers[0].input)) break;
                    fetch(slots[slot],id,request);
                    if(!q1.push(slot,workers[0].output)) break;
                }
                q1.close();
            });
            launch(1,[&] {
                std::size_t slot=0;
                while(!cancelled && q1.pop(slot,workers[1].input)) {
                    gray(slots[slot]); if(!q2.push(slot,workers[1].output)) break;
                } q2.close();
            });
            launch(2,[&] {
                std::size_t slot=0;
                while(!cancelled && q2.pop(slot,workers[2].input)) {
                    edges(slots[slot]); if(!q3.push(slot,workers[2].output)) break;
                } q3.close();
            });
            launch(3,[&] {
                std::size_t slot=0;
                while(!cancelled && q3.pop(slot,workers[3].input)) {
                    sink(slots[slot]); if(!free_slots.push(slot,workers[3].output)) break;
                }
            });
        } catch(...) {
            cancel(); for(auto& t:threads) t.join(); throw;
        }
    }
    const double setup_seconds=seconds(setup_start,Clock::now());
    const double cpu_start=cpu_seconds(false);
    start=Clock::now();
    free_slots.start(start); q1.start(start); q2.start(start); q3.start(start);
    if(pipeline) {
        { std::lock_guard lock(gate_mutex); gate_open=true; }
        gate_cv.notify_all();
        for(auto& t:threads) t.join();
        if(failure) std::rethrow_exception(failure);
    } else {
        std::ostringstream tid; tid<<std::this_thread::get_id();
        for(auto& worker:workers) worker.thread_id=tid.str();
        const double c=cpu_seconds(true);
        for(std::size_t id=0;id<o.frames;++id) {
            pace(id); const double request=stamp();
            fetch(slots[0],id,request); gray(slots[0]); edges(slots[0]); sink(slots[0]);
        }
        workers[0].cpu=cpu_seconds(true)-c; // Whole sequential thread, not Fetch alone.
    }
    const auto end=Clock::now();
    const double elapsed=seconds(start,end), cpu=cpu_seconds(false)-cpu_start;
    const double peak=peak_rss_mib();
    if(completed!=o.frames) throw std::runtime_error("incomplete run");
    std::array<QueueStats,4> queues{};
    queues[0]=free_slots.finish(end,elapsed); queues[1]=q1.finish(end,elapsed);
    queues[2]=q2.finish(end,elapsed); queues[3]=q3.finish(end,elapsed);
    std::vector<double> latency, request_latency, scheduled_latency, admission_lag;
    latency.reserve(o.frames); request_latency.reserve(o.frames); scheduled_latency.reserve(o.frames); admission_lag.reserve(o.frames);
    for(const auto& m:records) {
        latency.push_back((m.done-m.admit)*1000);
        request_latency.push_back((m.done-m.request)*1000);
        scheduled_latency.push_back((m.done-m.scheduled)*1000);
        admission_lag.push_back((m.admit-m.scheduled)*1000);
    }
    fs::create_directories(o.out);
    std::ofstream framecsv(o.out/"frames.csv"); framecsv.exceptions(std::ios::badbit|std::ios::failbit);
    framecsv<<std::setprecision(12)<<"frame_id,source_index,request_ms,admit_ms,done_ms,scheduled_ms,latency_ms,request_latency_ms,source_latency_ms,admission_lag_ms,pool_wait_ms,fetch_ms,gray_ms,sobel_ms,output_ms,fetch_begin_ms,fetch_end_ms,gray_begin_ms,gray_end_ms,sobel_begin_ms,sobel_end_ms,output_begin_ms,output_end_ms,sum,weighted_sum,slot_id\n";
    for(const auto& m:records) {
        framecsv<<m.id<<','<<m.id%source.count<<','<<m.request*1000<<','<<m.admit*1000<<','<<m.done*1000<<','<<m.scheduled*1000
          <<','<<(m.done-m.admit)*1000<<','<<(m.done-m.request)*1000<<','<<(m.done-m.scheduled)*1000<<','<<(m.admit-m.scheduled)*1000<<','<<(m.admit-m.request)*1000;
        for(std::size_t i=0;i<4;++i) framecsv<<','<<(m.end[i]-m.begin[i])*1000;
        for(std::size_t i=0;i<4;++i) framecsv<<','<<m.begin[i]*1000<<','<<m.end[i]*1000;
        framecsv<<','<<m.sum<<','<<m.weighted<<','<<m.slot_id<<'\n';
    } framecsv.close();
    std::ofstream wc(o.out/"workers.csv"); wc.exceptions(std::ios::badbit|std::ios::failbit);
    wc<<std::setprecision(12)<<"worker,service_s,cv_input_wait_s,cv_output_wait_s,input_wait_events,output_wait_events,cv_stall_pct,cpu_s,cpu_one_core_pct,pace_sleep_s,thread_id\n";
    for(std::size_t i=0;i<4;++i) {
        const auto& w=workers[i];
        wc<<i+1<<','<<w.service<<','<<w.input.seconds<<','<<w.output.seconds<<','<<w.input.events<<','<<w.output.events
          <<','<<100*(w.input.seconds+w.output.seconds)/elapsed<<',';
        if(pipeline) { if(std::isfinite(w.cpu)) wc<<w.cpu; }
        wc<<','; if(pipeline && std::isfinite(w.cpu)) wc<<100*w.cpu/elapsed;
        wc<<','<<w.pace_sleep<<','<<w.thread_id<<'\n';
    } wc.close();
    std::ofstream qc(o.out/"queues.csv"); qc.exceptions(std::ios::badbit|std::ios::failbit);
    qc<<"queue,capacity,time_weighted_mean,high_watermark\n"<<std::setprecision(12);
    const std::array<const char*,4> names={"free_pool","Q1","Q2","Q3"};
    if(pipeline) for(std::size_t i=0;i<4;++i)
        qc<<names[i]<<','<<(i?o.queue:slots_n)<<','<<queues[i].mean<<','<<queues[i].high<<'\n';
    qc.close();
    std::ofstream js(o.out/"summary.json"); js.exceptions(std::ios::badbit|std::ios::failbit);
    js<<std::setprecision(12)<<"{\n\"schema\":2,\n\"mode\":\""<<(pipeline?"pipeline":"sequential")<<"\",\n"
      <<"\"profile\":\""<<o.profile<<"\",\n\"edge_threshold\":"<<(o.profile=="source"?static_cast<int>(o.edge_threshold):-1)<<",\n"
      <<"\"reference_scope\":\""<<(o.profile=="source"?"Chen-2024-Sec4.4;US6553131B1-Fig1-block16-preprocessing-subset":"legacy-project-defined-affine-L1")<<"\",\n"
      <<"\"algorithm_id\":\""<<(o.profile=="source"?"chen-patent-edge-subset-v1":"affine-l1-v1")<<"\",\n"
      <<"\"allocation\":\""<<o.allocation<<"\",\n\"traversal\":\""<<o.traversal<<"\",\n\"io\":\""<<o.io<<"\",\n"
      <<"\"width\":"<<source.width<<",\n\"height\":"<<source.height<<",\n\"source_frames\":"<<source.count<<",\n\"frames\":"<<completed
      <<",\n\"rate\":"<<o.rate<<",\n\"queue_capacity\":"<<(pipeline?o.queue:0)<<",\n\"slot_count\":"<<slots_n
      <<",\n\"elapsed_s\":"<<elapsed<<",\n\"setup_s\":"<<setup_seconds<<",\n\"fps\":"<<static_cast<double>(completed)/elapsed
      <<",\n\"latency_p50_ms\":"<<quantile(latency,.5)<<",\n\"latency_p95_ms\":"<<quantile(latency,.95)<<",\n\"latency_p99_ms\":"<<quantile(latency,.99)
      <<",\n\"request_latency_p95_ms\":"<<quantile(request_latency,.95)<<",\n\"source_latency_p95_ms\":"<<quantile(scheduled_latency,.95)
      <<",\n\"admission_lag_p95_ms\":"<<quantile(admission_lag,.95)<<",\n\"admission_lag_last_ms\":"<<admission_lag.back()
      <<",\n\"process_cpu_s\":"; json_number(js,cpu);
    js<<",\n\"process_cpu_one_core_pct\":"; json_number(js,100*cpu/elapsed);
    js<<",\n\"logical_cpus_reported\":"<<std::thread::hardware_concurrency()<<",\n\"peak_process_rss_mib\":"; json_number(js,peak);
    js<<",\n\"frame_buffer_bound_bytes\":"<<frame_bound
      <<",\n\"setup_frame_array_allocations\":"<<1+(o.allocation=="pool"?3*slots_n:0)
      <<",\n\"timed_frame_array_allocations\":"<<(o.allocation=="dynamic"?3*completed:0)
      <<",\n\"capture_frames\":"<<o.capture<<",\n\"dropped_frames\":0,\n\"hardware_counters\":null,\n\"mean_stage_ms\":[";
    for(std::size_t i=0;i<4;++i) {if(i) js<<',';js<<workers[i].service*1000/static_cast<double>(completed);}
    js<<"],\n\"steady_output_fps\":";
    if(completed>20) {
        const auto a=completed/10,b=completed-1-completed/10;
        json_number(js,static_cast<double>(b-a)/(records[b].done-records[a].done));
    } else js<<"null";
    js<<"\n}\n"; js.close();
    if(capture_bytes) {
        std::ofstream dump(o.out/"captured_edges.raw",std::ios::binary); dump.exceptions(std::ios::badbit|std::ios::failbit);
        dump.write(reinterpret_cast<const char*>(captured.get()),static_cast<std::streamsize>(capture_plane_bytes)); dump.close();
        std::ofstream gdump(o.out/"captured_gray.raw",std::ios::binary); gdump.exceptions(std::ios::badbit|std::ios::failbit);
        gdump.write(reinterpret_cast<const char*>(captured.get()+capture_plane_bytes),static_cast<std::streamsize>(capture_plane_bytes)); gdump.close();
        if(o.profile=="source") {
            std::ofstream bdump(o.out/"captured_binary.raw",std::ios::binary); bdump.exceptions(std::ios::badbit|std::ios::failbit);
            bdump.write(reinterpret_cast<const char*>(captured.get()+2*capture_plane_bytes),static_cast<std::streamsize>(capture_plane_bytes)); bdump.close();
        }
    }
    // Output files are published last by creating a success marker after all writes.
    std::ofstream marker(o.out/"SUCCESS"); marker.exceptions(std::ios::badbit|std::ios::failbit);
    marker<<"complete\n"; marker.close();
    std::cout<<std::fixed<<std::setprecision(3)<<"frames="<<completed<<" fps="<<static_cast<double>(completed)/elapsed
      <<" p95_ms="<<quantile(latency,.95)<<" output="<<o.out.string()<<'\n';
    return 0;
  } catch(const std::exception& e) { std::cerr<<"ERROR: "<<e.what()<<'\n'; return 1; }
    catch(...) { std::cerr<<"ERROR: unknown failure\n"; return 1; }
}
}
