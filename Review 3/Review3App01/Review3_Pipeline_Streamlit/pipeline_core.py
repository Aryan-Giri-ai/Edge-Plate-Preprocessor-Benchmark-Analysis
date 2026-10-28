"""Native sequential/pipeline execution, trace checks and matched evaluation."""
from pathlib import Path
import csv,hashlib,io,json,os,random,struct,subprocess,tempfile,zipfile
import numpy as np
from image_ops import luminance,contrast,gradient,threshold_map,close_map,png_bytes

ROOT=Path(__file__).resolve().parent
STAGES=["fetch","gray","sobel","output"]
NAMES=["W1 Fetch","W2 Gray / contrast","W3 Sobel / threshold / closing","W4 Output / recycle"]
def executable(mode):
    return ROOT/"native"/"bin"/(("edge_seq" if mode=="B" else "edge_pipeline")+(".exe" if os.name=="nt" else ""))
def ready():
    return all(executable(m).is_file() for m in ["B","D"])
def validate_images(images):
    if not 1<=len(images)<=12:raise ValueError("Select 1 to 12 source images.")
    shape=images[0].shape
    if any(x.dtype!=np.uint8 or x.shape!=shape for x in images):raise ValueError("All selected RGB8 images must share their original dimensions; no resizing is performed.")
    if len(shape)!=3 or shape[2]!=3 or min(shape[:2])<3 or max(shape[:2])>8192 or shape[0]*shape[1]>4_000_000:
        raise ValueError("Use original images from 3x3 up to 4 megapixels and at most 8192 pixels per side.")
def write_replay(images,path):
    validate_images(images);h,w=images[0].shape[:2]
    with path.open("wb") as f:
        f.write(b"EPRAW01\n"+struct.pack("<III",w,h,len(images)))
        for a in images:f.write(a.tobytes())
def read_csv(path):
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def invoke(mode,data,out,frames,capture,threshold,queue):
    exe=executable(mode)
    if not exe.is_file():raise FileNotFoundError("Build both native engines first with bash native/build.sh in MSYS2 UCRT64.")
    cmd=[str(exe),"--input",str(data),"--out",str(out),"--frames",str(frames),"--capture",str(capture),
         "--allocation","pool","--traversal","row","--slots","34","--queue",str(queue),
         "--profile","source","--edge-threshold",str(threshold),"--rate","0","--io","file"]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=1800)
    if result.returncode:raise RuntimeError("Native execution failed: "+(result.stderr or result.stdout or str(result.returncode))+
                                            ". Check the UCRT64 runtime bin directory on PATH.")
    if not (out/"SUCCESS").exists():raise RuntimeError("Incomplete native execution.")
    run={"summary":json.loads((out/"summary.json").read_text()),"frames":read_csv(out/"frames.csv"),
         "workers":read_csv(out/"workers.csv"),"queues":read_csv(out/"queues.csv")}
    run["audit"]=audit_trace(run,mode,frames)
    if capture:
        s=run["summary"];h,w=s["height"],s["width"]
        run["planes"]={k:np.frombuffer((out/name).read_bytes(),np.uint8).reshape(capture,h,w).copy()
            for k,name in {"gray":"captured_gray.raw","binary":"captured_binary.raw","closed":"captured_edges.raw"}.items()}
    return run
def fingerprints(run):
    return [(r["source_index"],r["sum"],r["weighted_sum"]) for r in run["frames"]]
def events(run):
    return [{"frame":int(r["frame_id"]),"source":int(r["source_index"]),"slot":int(r["slot_id"]),
             "worker":i+1,"stage":NAMES[i],"begin":float(r[s+"_begin_ms"]),"end":float(r[s+"_end_ms"])}
            for r in run["frames"] for i,s in enumerate(STAGES)]
def audit_trace(run,mode,count):
    s=run["summary"];rows=run["frames"]
    expected="sequential" if mode=="B" else "pipeline"
    if s["mode"]!=expected or len(rows)!=count or s["frames"]!=count:raise ValueError("Mode/frame count audit failed.")
    if s["algorithm_id"]!="chen-patent-edge-subset-v1":raise ValueError("Unexpected numerical profile.")
    nids=len({r["thread_id"] for r in run["workers"]})
    if nids!=(1 if mode=="B" else 4):raise ValueError("Unexpected native thread identity count.")
    laststage=[-1.0]*4;lastslot={};sweep=[]
    for index,r in enumerate(rows):
        if int(r["frame_id"])!=index or int(r["source_index"])!=index%s["source_frames"]:raise ValueError("Frame/source order failed.")
        slot=int(r["slot_id"]);prev=float(r["admit_ms"])
        if not 0<=slot<s["slot_count"]:raise ValueError("Invalid slot.")
        if float(r["fetch_begin_ms"])+1e-6<lastslot.get(slot,-1):raise ValueError("Premature slot reuse.")
        for i,stage in enumerate(STAGES):
            b,e=float(r[stage+"_begin_ms"]),float(r[stage+"_end_ms"])
            if b+1e-6<prev or e<b or b+1e-6<laststage[i]:raise ValueError("Invalid frame-stage or worker order.")
            prev=e;laststage[i]=e
            if e>b:sweep.extend([(b,1),(e,-1)])
        lastslot[slot]=float(r["output_end_ms"])
    active=peak=0
    for _,change in sorted(sweep):active+=change;peak=max(active,peak)
    if mode=="B" and peak!=1:raise ValueError("Sequential stage intervals overlap.")
    for r in run["queues"]:
        if not 0<=float(r["time_weighted_mean"])<=int(r["high_watermark"])<=int(r["capacity"]):
            raise ValueError("Queue capacity audit failed.")
    return {"passed":True,"thread_id_count":nids,"peak_wall_interval_overlap":peak,
            "scope":"order, source indices, worker identities, slot ownership and queue bounds; wall overlap includes preemption"}
def settings_check(images,frames,threshold,queue):
    validate_images(images)
    if not 1<=frames<=10000 or not 0<=threshold<=1020 or queue not in [2,5,10]:raise ValueError("Invalid run settings.")
def run_demo(images,frames=120,capture=3,threshold=80,queue=5):
    settings_check(images,frames,threshold,queue)
    if not 1<=capture<=min(frames,6):raise ValueError("Capture must be 1..6 and <= frame count.")
    with tempfile.TemporaryDirectory(prefix="review3_demo_") as temp:
        root=Path(temp);data=root/"input.epraw";write_replay(images,data)
        runs={mode:invoke(mode,data,root/mode,frames,capture,threshold,queue) for mode in ["B","D"]}
        if fingerprints(runs["B"])!=fingerprints(runs["D"]):raise ValueError("All-frame output fingerprints differ.")
        for k in ["gray","binary","closed"]:
            if not np.array_equal(runs["B"]["planes"][k],runs["D"]["planes"][k]):raise ValueError("Captured plane mismatch: "+k)
        for i in range(capture):
            gray=contrast(luminance(images[i%len(images)]))
            binary=threshold_map(gradient(gray),threshold);closed=close_map(binary)
            for key,a in [("gray",gray),("binary",binary),("closed",closed)]:
                if not np.array_equal(a,runs["D"]["planes"][key][i]):raise ValueError("Reference mismatch: "+key)
        return {"runs":runs,"source_count":len(images),"replay_sha256":hashlib.sha256(data.read_bytes()).hexdigest(),
                "source_rgb_sha256":[hashlib.sha256(a.tobytes()).hexdigest() for a in images],
                "frames":frames,"capture":capture,"threshold":threshold,"queue":queue,"slots":34,
                "correctness":"B/D captured gray, binary and final maps match byte for byte and the Python equivalent; all-frame fingerprints match",
                "scope":"Capture-enabled demonstration; not a primary benchmark."}
def benchmark(images,frames=600,repeats=3,warmup=60,threshold=80,queue=5,progress=None):
    settings_check(images,frames,threshold,queue)
    if not 3<=repeats<=10 or not 0<=warmup<=1000:raise ValueError("Use 3..10 paired blocks and 0..1000 warmup frames.")
    rng=random.Random(260826);records=[];ratios=[];canonical=None
    with tempfile.TemporaryDirectory(prefix="review3_bench_") as temp:
        root=Path(temp);data=root/"input.epraw";write_replay(images,data)
        digest=hashlib.sha256(data.read_bytes()).hexdigest()
        for block in range(1,repeats+1):
            order=["B","D"];rng.shuffle(order);pair={}
            for mode in order:
                if warmup:invoke(mode,data,root/f"warmup_{block}_{mode}",warmup,0,threshold,queue)
                run=invoke(mode,data,root/f"run_{block}_{mode}",frames,0,threshold,queue)
                fp=fingerprints(run)
                if canonical is None:canonical=fp
                elif fp!=canonical:raise ValueError("Benchmark fingerprint mismatch.")
                pair[mode]=run["summary"]["fps"]
                records.append({"block":block,"mode":mode,**run})
                if progress:progress(len(records)/(2*repeats))
            ratios.append(pair["D"]/pair["B"])
    logs=np.log(ratios);rng_np=np.random.default_rng(260826)
    boots=np.exp(np.mean(rng_np.choice(logs,size=(10000,repeats),replace=True),axis=1))
    low,high=np.quantile(boots,[.025,.975])
    return {"runs":records,"frames":frames,"repeats":repeats,"warmup":warmup,"source_count":len(images),
            "dataset_sha256":digest,"threshold":threshold,"queue":queue,"slots":34,"capture":0,
            "paired_ratio":float(np.exp(logs.mean())),"ci95":[float(low),float(high)],
            "scope":"Exploratory when repeats <10 or runs are short; no guarantee of speedup.",
            "minimum_run_seconds":min(r["summary"]["elapsed_s"] for r in records)}

def event_rows_at(run,clock):
    active=[e for e in events(run) if e["begin"]<=clock<e["end"]]
    return [{"worker":i,"active_frame":next((e["frame"] for e in active if e["worker"]==i),None)}
            for i in range(1,5)]
def captured_images(images,result,index):
    source=images[index%len(images)];p=result["runs"]["D"]["planes"];b=result["runs"]["B"]["planes"]
    rawgray=luminance(source);g=gradient(p["gray"][index])
    return {"input":source,"grayscale":rawgray,"contrast":p["gray"][index],
            "sobel_preview":np.rint(g*255/1020).astype(np.uint8),"binary":p["binary"][index],
            "closed":p["closed"][index],"baseline":b["closed"][index],
            "difference":np.abs(p["closed"][index].astype(np.int16)-b["closed"][index]).astype(np.uint8),
            "closing_change":np.abs(p["closed"][index].astype(np.int16)-p["binary"][index]).astype(np.uint8)}
def json_without_planes(value):
    if isinstance(value,dict):return {k:json_without_planes(v) for k,v in value.items() if k!="planes"}
    if isinstance(value,list):return [json_without_planes(v) for v in value]
    return value
def export_result(images,result,names,bench=None):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
        meta=json_without_planes(result);meta["source_names"]=names
        z.writestr("demo.json",json.dumps(meta,indent=2,allow_nan=False))
        for i in range(result["capture"]):
            for name,a in captured_images(images,result,i).items():z.writestr(f"images/{i:03d}_{name}.png",png_bytes(a))
        for mode,run in result["runs"].items():
            for key in ["frames","workers","queues"]:
                if not run[key]:continue
                s=io.StringIO();w=csv.DictWriter(s,fieldnames=list(run[key][0]));w.writeheader();w.writerows(run[key])
                z.writestr(f"{mode}/{key}.csv",s.getvalue())
        if bench is not None:z.writestr("benchmark.json",json.dumps(bench,indent=2,allow_nan=False))
    return buf.getvalue()

