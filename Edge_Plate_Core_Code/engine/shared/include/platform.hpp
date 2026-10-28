#pragma once
#include <cstdint>
#include <limits>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <psapi.h>
#else
#include <sys/resource.h>
#include <time.h>
#endif

namespace edge {
inline double cpu_seconds(bool thread) {
#ifdef _WIN32
    FILETIME created, ended, kernel, user;
    const BOOL ok = thread ? GetThreadTimes(GetCurrentThread(), &created, &ended, &kernel, &user)
                           : GetProcessTimes(GetCurrentProcess(), &created, &ended, &kernel, &user);
    if (!ok) return std::numeric_limits<double>::quiet_NaN();
    auto ticks=[](FILETIME f) {return (static_cast<std::uint64_t>(f.dwHighDateTime)<<32) | f.dwLowDateTime;};
    return static_cast<double>(ticks(kernel)+ticks(user))*1e-7;
#else
    timespec t{};
    if (clock_gettime(thread ? CLOCK_THREAD_CPUTIME_ID : CLOCK_PROCESS_CPUTIME_ID, &t))
        return std::numeric_limits<double>::quiet_NaN();
    return static_cast<double>(t.tv_sec)+static_cast<double>(t.tv_nsec)*1e-9;
#endif
}
inline double peak_rss_mib() {
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS m{}; m.cb=sizeof(m);
    if (!GetProcessMemoryInfo(GetCurrentProcess(), &m, sizeof(m)))
        return std::numeric_limits<double>::quiet_NaN();
    return static_cast<double>(m.PeakWorkingSetSize)/(1024*1024);
#else
    rusage r{};
    if (getrusage(RUSAGE_SELF,&r)) return std::numeric_limits<double>::quiet_NaN();
    return static_cast<double>(r.ru_maxrss)/1024; // Linux reports KiB.
#endif
}
}
