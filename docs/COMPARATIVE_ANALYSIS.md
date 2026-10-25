# How to compare the programs and defend the conclusions

## 1. Establish that the comparison is valid

Use your laptop's results for claims about that target machine. The included Linux measurements use an explicitly selected UFPR sample; independent synthetic cases check numerical correctness. The default `--profile source` uses fixed contrast, vertical Sobel, binary threshold and closing. First run the independent correctness checks and full-byte verification on the actual dataset. Then use the same **profile and edge threshold**, dataset hash, image order, frame count, IO mode, compiler flags, output work, power mode and pipeline slot count in every paired run. Sequential B uses one slot; pipeline treatments all use 34. The analyzer rejects stale algorithm IDs, mixed profiles or thresholds. `sobel_ms` and `sobel_mean_ms_median` include the entire Sobel/threshold/closing stage. The original archive's timings concern the legacy workload and are not evidence for this default.

The main benchmark is unpaced. Complete at least ten repetition blocks with randomized configuration order and sufficiently long runs. Keep every successful run from the planned experiment. Do not select the fastest pipeline result and compare it with the slowest baseline result. If a run was affected by a documented external disturbance, retain it, state the exclusion rule, and rerun the affected complete block in a fresh experiment rather than silently removing it.

This package does not impose a desired outcome on measurements. A slowdown, unclear result or latency regression can be a valid architecture finding.

## 2. Use the right comparison for each claim

| Comparison | Claim it can test | What remains bundled |
|:---|:---|:---|
| B / A | Effect of reusing storage in a sequential loop | Allocation and buffer-lifetime/page/cache effects |
| C / A | Effect of adding the four-stage pipeline with dynamic arrays retained | Synchronization, scheduling, cross-thread allocation/free, larger in-flight working set |
| D / B | **Primary:** effect of the four-stage pipeline with storage reuse in both | Pipeline synchronization and necessarily larger concurrent working set |
| D / C | Effect of reusing frame arrays inside the pipeline | Retained memory, allocator behavior and address/page reuse |
| D / E1; E3 / D | Queue capacities 2→5 and 5→10 | Pool stays fixed at 34; achieved active-frame count can change |
| D / F | Row traversal versus column traversal in gray, Sobel and closing | Cache access, prefetching, vectorization and loop overhead can all change |
| D / A | Combined implementation change | Cannot attribute the whole gain to threading |

The ratio is candidate FPS / baseline FPS. Values above 1 favor the candidate. `comparisons.csv` implements these directions. D and E2 are identical; measuring both under different labels would duplicate the same treatment.

## 3. Fill the result table with measured values

Open `aggregate.csv` and `comparisons.csv`. Report, for each configuration:

| Required entry | Where it comes from |
|:---|:---|
| FPS and run-to-run range | `fps_median`, `fps_min`, `fps_max` |
| Speedup with uncertainty | `paired_speedup`, `ci95_low`, `ci95_high` in comparisons |
| P50/P95/P99 frame latency | Medians of each run's latency percentile in aggregate |
| Stage times | `fetch/gray/sobel/output_mean_ms_median` |
| Stage waits | Per-run `workers.csv`, input and output waits separately |
| Queue mean/high-water | Per-run `queues.csv`, Q1/Q2/Q3 separately |
| Allocation churn | `timed_frame_array_allocations`; state these are three pixel-array allocations per dynamic frame |
| Process memory | `peak_rss_mib_median` and the calculated frame-buffer bound |
| CPU utilization convention | `cpu_one_core_pct_median`; 100% means one CPU-equivalent second per wall second |
| Paced-source behavior | Source latency, last admission lag, per-frame lag over time |
| IPC/cache events | Separate profiler export, or explicitly “not measured” |

Avoid pooling thousands of correlated frame observations and treating them as thousands of independent performance experiments. The independent experimental unit here is a process run/block. The report aggregates per-run P95 values; it does not claim they are the pooled-frame P95.

For one matched pair with equal frame count N:

```text
FPS = N / elapsed_seconds
speedup = FPS_candidate / FPS_baseline = T_baseline / T_candidate
throughput_gain_percent = (speedup - 1) * 100
elapsed_time_reduction_percent = (1 - 1/speedup) * 100
```

Throughput gain and elapsed-time reduction are different percentages. The automatic comparison computes the geometric mean of paired per-block FPS ratios and a 95% percentile-bootstrap interval from 10,000 resamples of paired log ratios. Three-block pilot intervals are exploratory; the report refuses to call their direction established.

For the main, preselected D/B hypothesis, an interval entirely above 1 supports a throughput improvement on the tested setup. An interval crossing 1 leaves the direction unresolved by this experiment. An interval entirely below 1 supports a slowdown. Practical usefulness additionally depends on your latency and memory budgets. The supporting A–F comparisons are exploratory unless you predefine a broader statistical testing plan; their many intervals do not jointly guarantee a 95% family-wise confidence level.

## 4. Compare observed behavior with pipeline theory

Let the sequential mean service times per frame be t1, t2, t3 and t4. In an ideal model with fixed stage durations, no synchronization cost or resource contention:

```text
sequential time for N frames = N * (t1+t2+t3+t4)
pipeline time for N frames = (t1+t2+t3+t4) + (N-1)*max(t1,t2,t3,t4)
large-N ideal speedup = (t1+t2+t3+t4) / max(t1,t2,t3,t4) <= 4
```

Use B's measured stage means to compute the first-order pooled-pipeline estimate; the analyzer does this automatically. Compare with D/B's actual measured speedup. The estimate is conditional on equal service costs and ideal resources. Real pipeline stage times change with concurrency, caching and OS scheduling, so it is not an inviolable empirical upper bound. If a measurement exceeds it, recheck timing boundaries and changed service costs instead of declaring a theory violation.

The i5-10300H has four physical cores and eight threads according to Intel's specifications. Four software workers may overlap on that CPU, but one worker cannot make another stage finish faster. Eight logical threads do not imply 8× speedup for a four-stage design. Sustained clock frequency, power, memory behavior and synchronization still matter. The program does not pin workers to four dedicated cores.

If the Sobel stage dominates the **measured** sequential time, the ideal speedup will be much lower than four. It is also possible for Fetch, Gray/Contrast or Output to be longest. The shared output copy and verification pass are real work in this baseline; do not silently disable them only in the pipeline to obtain a higher FPS.

## 5. Diagnose the actual limiting stage

Inspect stage means and their distributions, then use waits and queue occupancy to support the interpretation:

| Observation | Supported interpretation to investigate |
|:---|:---|
| Gray spends time waiting to push Q2, Q2 is often high, and Sobel has the longest service time | Sobel is a candidate throughput limiter under this workload |
| Sobel waits for Q2 input and Fetch has high read time | Input/earlier-stage supply may limit throughput |
| Q3 is frequently high and Output service is long | Output copying/verification may limit the measured pipeline |
| Small inputs have frequent waits and little useful work | Thread/queue overhead may dominate useful per-frame work |
| Pipeline stage means grow relative to B, with little FPS improvement | Scheduling or shared-resource contention merits profiling |
| Most free slots remain available | Slot supply is not the observed bottleneck |

These are interpretations of combined evidence, not proofs of a hardware cause. “Sobel is memory bound” requires appropriate hardware profiling. A stencil's array accesses or a long wall-clock interval alone cannot establish DRAM-bandwidth saturation.

## 6. Quantify the queue trade-off

Compare E1, D/E2 and E3 with the same 34 slots. Plot or tabulate median FPS, P95/P99 latency, Q1/Q2/Q3 time-weighted occupancy, high-water marks and blocked producer time. Use the raw per-run values to show variability.

A useful queue increase may reduce short bursts of blocking and increase throughput. A larger queue can also allow more frames to wait without changing the slowest stage's rate. If q=10 produces essentially the same FPS as q=5 with worse latency, the extra queue depth did not improve the selected operating point. Do not assume capacity 5 is optimal before measuring it.

The package records occupancy mean/high-water, not a time series of every queue event. Frame timestamps can show stage overlap and inter-stage delays, but they cannot reconstruct every queue push/pop timestamp exactly. A queue-occupancy-over-time plot requires an additional instrumented tracing experiment; label that as further work rather than inventing samples.

## 7. Assess 30 and 60 FPS behavior

For a rate r, the ideal stage-capacity condition is `max(t_i) <= 1000/r` milliseconds, giving about 33.33 ms at 30 FPS or 16.67 ms at 60 FPS. This is necessary under the simple model and insufficient to guarantee real execution. Whole-frame latency may exceed one arrival interval while the pipeline still sustains the rate.

At 30 FPS, both fast configurations can report approximately 30 output FPS even if one has much more spare capacity. Use unpaced runs to compare maximum throughput. In paced runs inspect:

1. Whether actual throughput approaches the offered rate over the long replay.
2. Whether `admission_lag_ms` grows over frame index instead of staying bounded around scheduling jitter.
3. Whether `source_latency_ms` stays within a separately stated application budget.
4. Whether processing P95/P99 and queue occupancy remain acceptable.

This replay preserves every frame by blocking. It cannot claim a live-camera frame-drop rate of zero or hard real-time service. If admission lag grows, describe overload even if admitted-frame latency looks modest. Do not relabel a bounded internal queue as proof that the upstream source is keeping up.

## 8. Measure cache and CPU behavior only with actual counters

The supplied programs collect CPU time, peak process memory, service intervals and synchronization data. They do not collect hardware events in MSYS2. Leave cache misses, IPC and bandwidth as **not measured** until you have a supported profiler export.

On Windows, Intel VTune provides CPU profiling and, when supported by the processor/OS/driver, Microarchitecture Exploration. See the [official analysis documentation](https://www.intel.com/content/www/us/en/docs/vtune-profiler/user-guide/2026-0/general-exploration-analysis.html). Run its system capability checks; the presence of an Intel CPU does not guarantee every event is available in the current environment.

Practical procedure:

1. Preserve the unprofiled benchmark results as the primary timing evidence.
2. Open VTune on the same Windows machine and configure a local application target for `baseline/build/edge_seq.exe` or `pipeline/build/edge_pipeline.exe`, with the project directory as working directory. Ensure the UCRT64 runtime directory is available in the target's PATH.
3. Supply the same input, frame count and configuration arguments used in the unpaced experiment, with a new output directory for each launch.
4. Start with Hotspots to identify expensive functions/workers. For cache/IPC claims, use a supported hardware-event analysis and retain the exact event names and profiler warnings.
5. Export D and F measurements for the same workload. Inspect cycle/instruction totals, IPC and relevant cache or memory metrics only where actually supported. Record sample coverage/multiplexing and any unavailable counters.
6. State that profiler launch measurements may include setup, preload and exit/logging; this package has no profiler-specific region markers. Use long runs and inspect the processing functions, but do not pretend whole-process events precisely match the C++ timed region.

Do not type Linux `perf` commands in MSYS2 and assume they profile native Windows events. A Linux/WSL benchmark is a different OS environment. If profiling is unavailable, the defensible statement is that row traversal changed runtime while the hardware cause remains unverified.

## 9. Write the conclusion from the result pattern

Use the measured values to complete a statement of this form:

“On the Intel Core i5-10300H laptop under [Windows/toolchain/power settings], using [dataset selection/hash], [resolution] and [IO mode], the pooled four-worker pipeline achieved [FPS] versus [FPS] for the pooled sequential baseline. The paired speedup was [ratio], with a 95% interval of [low, high]. P95 admitted-frame latency changed from [value] to [value], and peak process memory changed from [value] to [value]. [Stage] had the longest measured service interval; [wait/queue evidence] supported its role as a candidate limiter. The results [support/do not establish/show a regression in] throughput improvement for this workload. [Any unmeasured hardware mechanism] remains unverified.”

Then add only the isolated conclusions supported by A/B, A/C, C/D, the queue sweep and D/F. If the data show improvement with worse latency, say both. If pooling removes allocation calls but does not make execution faster, say both. If no meaningful speedup appears, the project still characterizes the limits of this architecture.

Do not claim OCR improvement, a new Sobel algorithm, guaranteed 4× speedup, maximum possible hardware utilization, 95% cache hits, eliminated pixel copies, a validated frame-drop policy, energy savings or hard real-time operation from this experiment.
