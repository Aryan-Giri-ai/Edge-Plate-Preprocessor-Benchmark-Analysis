#pragma once
#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <mutex>
#include <stdexcept>
#include <vector>

namespace edge {
using Clock = std::chrono::steady_clock;
using Time = Clock::time_point;
inline double seconds(Time a, Time b) { return std::chrono::duration<double>(b-a).count(); }
struct Wait { double seconds=0; std::size_t events=0; };
struct QueueStats { double mean=0; std::size_t high=0; };

// Preallocated FIFO ring of slot IDs. One mutex protects ownership and metrics.
class Queue {
    std::vector<std::size_t> ring_;
    std::size_t head_=0, tail_=0, depth_=0, high_=0;
    bool closed_=false;
    std::mutex mutex_;
    std::condition_variable readable_, writable_;
    Time last_=Clock::now();
    double integral_=0;
    void integrate(Time t) {
        integral_ += static_cast<double>(depth_) * seconds(last_, t);
        last_=t;
    }
public:
    explicit Queue(std::size_t capacity): ring_(capacity) {
        if (!capacity) throw std::invalid_argument("queue capacity must be positive");
    }
    void seed(std::size_t id) {
        if (depth_ == ring_.size()) throw std::logic_error("pool seed overflow");
        ring_[tail_]=id; tail_=(tail_+1)%ring_.size(); ++depth_;
    }
    // Called before workers are released.
    void start(Time t) { last_=t; integral_=0; high_=depth_; }
    bool push(std::size_t id, Wait& wait) {
        std::unique_lock lock(mutex_);
        if (!closed_ && depth_==ring_.size()) {
            auto t=Clock::now(); ++wait.events;
            writable_.wait(lock, [&]{ return closed_ || depth_<ring_.size(); });
            wait.seconds += seconds(t,Clock::now());
        }
        if (closed_) return false;
        integrate(Clock::now());
        ring_[tail_]=id; tail_=(tail_+1)%ring_.size(); ++depth_;
        high_=std::max(high_,depth_);
        lock.unlock(); readable_.notify_one(); return true;
    }
    bool pop(std::size_t& id, Wait& wait) {
        std::unique_lock lock(mutex_);
        if (!closed_ && depth_==0) {
            auto t=Clock::now(); ++wait.events;
            readable_.wait(lock, [&]{ return closed_ || depth_>0; });
            wait.seconds += seconds(t,Clock::now());
        }
        if (depth_==0) return false;
        integrate(Clock::now());
        id=ring_[head_]; head_=(head_+1)%ring_.size(); --depth_;
        lock.unlock(); writable_.notify_one(); return true;
    }
    void close() {
        { std::lock_guard lock(mutex_); closed_=true; }
        readable_.notify_all(); writable_.notify_all();
    }
    QueueStats finish(Time t, double duration) {
        std::lock_guard lock(mutex_); integrate(t);
        return {integral_/duration, high_};
    }
};
}
