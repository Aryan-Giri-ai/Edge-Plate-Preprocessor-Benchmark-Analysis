#!/usr/bin/env python3
"""Summarize runs, using runs (not correlated frames) as comparison units."""
import argparse
import csv
import json
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path
from common import ALGORITHM_IDS

PAIRS = [("A","B","Buffer reuse in sequential"), ("A","C","Pipeline with dynamic buffers"),
         ("B","D","Primary concurrency comparison with reuse"), ("C","D","Pooling inside pipeline"),
         ("E1","D","Queue capacity 2 to 5"), ("D","E3","Queue capacity 5 to 10"),
         ("F","D","Column traversal to row traversal"), ("A","D","Combined change; effects not isolated")]

def q(values, p):
    v = sorted(values)
    x = (len(v)-1)*p
    lo = int(x)
    return v[lo] + (v[min(lo+1,len(v)-1)]-v[lo])*(x-lo)

def paired_ci(ratios):
    logs = [math.log(x) for x in ratios]
    estimate = math.exp(st.mean(logs))
    if len(logs) < 2:
        return estimate, None, None
    rng = random.Random(20260826)
    means = [st.mean(rng.choices(logs,k=len(logs))) for _ in range(10000)]
    return estimate, math.exp(q(means,.025)), math.exp(q(means,.975))

def csv_out(path, rows):
    if rows:
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("experiment", type=Path)
    a = p.parse_args()
    info = json.loads((a.experiment/"experiment.json").read_text(encoding="utf-8"))
    if not info.get("complete"):
        raise ValueError("Experiment incomplete. Inspect the failed run; do not publish partial comparisons.")
    groups = defaultdict(list)
    raw = []
    for entry in info["runs"]:
        folder = a.experiment/entry["path"]
        if not entry.get("fingerprints_match") or not (folder/"SUCCESS").is_file():
            raise ValueError("Missing correctness/success marker")
        s = json.loads((folder/"summary.json").read_text())
        expected_profile=info.get("profile","legacy")
        if s.get("profile","legacy")!=expected_profile:
            raise ValueError("Mixed algorithm profiles; only compare identical work")
        if expected_profile=="source" and s.get("edge_threshold")!=info.get("edge_threshold"):
            raise ValueError("Mixed edge thresholds; only compare identical work")
        if s.get("algorithm_id") != ALGORITHM_IDS[expected_profile] or info.get("algorithm_id") != ALGORITHM_IDS[expected_profile]:
            raise ValueError("Stale or mixed algorithm revisions; use fresh results from the current build")
        if s["capture_frames"]:
            raise ValueError("Captured runs cannot be used as primary benchmark results")
        s.update(config=entry["config"], block=entry["block"])
        groups[(entry["rate"],entry["config"])].append(s)
        raw.append({k:v for k,v in s.items() if not isinstance(v,(list,dict))})
    csv_out(a.experiment/"all_runs.csv", raw)
    aggregates = []
    for (rate,config), runs in sorted(groups.items()):
        med = lambda k: st.median(r[k] for r in runs if r[k] is not None)
        aggregate = dict(rate=rate, config=config, runs=len(runs), fps_median=med("fps"),
                         profile=info.get("profile","legacy"), edge_threshold=info.get("edge_threshold",-1),
                         fps_min=min(r["fps"] for r in runs), fps_max=max(r["fps"] for r in runs),
                         p50_ms_median=med("latency_p50_ms"), p95_ms_median=med("latency_p95_ms"),
                         p99_ms_median=med("latency_p99_ms"),
                         source_p95_ms_median=med("source_latency_p95_ms"),
                         admission_lag_last_ms_median=med("admission_lag_last_ms"),
                         peak_rss_mib_median=med("peak_process_rss_mib") if all(r["peak_process_rss_mib"] is not None for r in runs) else "",
                         cpu_one_core_pct_median=med("process_cpu_one_core_pct") if all(r["process_cpu_one_core_pct"] is not None for r in runs) else "",
                         timed_frame_array_allocations=med("timed_frame_array_allocations"))
        for i,name in enumerate(["fetch","gray","sobel","output"]):
            aggregate[name+"_mean_ms_median"] = st.median(r["mean_stage_ms"][i] for r in runs)
        aggregates.append(aggregate)
    csv_out(a.experiment/"aggregate.csv",aggregates)
    comparisons=[]
    for rate in sorted({k[0] for k in groups}):
        for base,candidate,purpose in PAIRS:
            before={r["block"]:r for r in groups.get((rate,base),[])}
            after={r["block"]:r for r in groups.get((rate,candidate),[])}
            if not before or not after:
                continue
            if before.keys()!=after.keys():
                raise ValueError("Unpaired blocks")
            ratios=[after[b]["fps"]/before[b]["fps"] for b in sorted(before)]
            estimate,lo,hi=paired_ci(ratios)
            interpretation="insufficient repetitions" if len(ratios)<5 else (
                "throughput improvement supported" if lo>1 else "throughput regression supported" if hi<1 else "direction inconclusive")
            if rate:
                interpretation="paced comparison: inspect source delay and admission lag; FPS is source constrained"
            comparisons.append(dict(rate=rate, baseline=base, candidate=candidate, purpose=purpose,
                                    pairs=len(ratios), paired_speedup=estimate, ci95_low=lo, ci95_high=hi,
                                    throughput_gain_pct=100*(estimate-1), conclusion=interpretation))
    csv_out(a.experiment/"comparisons.csv",comparisons)
    lines=["# Measured preprocessing comparison", "",
           f"Algorithm profile: **{info.get('profile','legacy')}**. Edge threshold: {info.get('edge_threshold','not applicable')}.", "",
           f"Input kind: **{info['dataset_manifest']['kind']}**. OS: {info['platform']}.", "",
           "These results belong to the recorded machine and selected workload. Replayed frames are not additional distinct source images. Synthetic input, when selected, establishes software behavior only.", "",
           "Run order was randomized within complete blocks. Each run is one observation. Latency columns below are medians of per-run percentiles.", "",
           "| Input FPS | Config | Runs | Median FPS | P50 ms | P95 ms | P99 ms | Source P95 ms |",
           "|---:|:---|---:|---:|---:|---:|---:|---:|"]
    for r in aggregates:
        lines.append(f"| {r['rate']:g} | {r['config']} | {r['runs']} | {r['fps_median']:.3f} | {r['p50_ms_median']:.3f} | {r['p95_ms_median']:.3f} | {r['p99_ms_median']:.3f} | {r['source_p95_ms_median']:.3f} |")
    lines += ["", "| Input FPS | Comparison | Paired speedup | 95% bootstrap interval | Interpretation |",
              "|---:|:---|---:|:---|:---|"]
    for r in comparisons:
        ci="unavailable" if r["ci95_low"] is None else f"{r['ci95_low']:.3f} to {r['ci95_high']:.3f}"
        lines.append(f"| {r['rate']:g} | {r['candidate']} / {r['baseline']} | {r['paired_speedup']:.3f} | {ci} | {r['conclusion']} |")
    lines += ["", "Intervals use a deterministic percentile bootstrap of paired log FPS ratios (10,000 resamples). With fewer than five blocks, treat all estimates as exploratory. Ten or more blocks are preferred. Intervals do not account for selection across many comparisons or a shared external confound.", "",
              "The primary comparison is D/B at unpaced input. A/D combines allocation and scheduling changes. No claim about cache misses, memory bandwidth, OCR accuracy, energy or hard real-time behavior follows from FPS alone.", "",
              "## Stage-balance estimate", ""]
    for (rate,config),runs in sorted(groups.items()):
        if rate!=0 or config not in {"A","B"}: continue
        t=[st.median(r["mean_stage_ms"][i] for r in runs) for i in range(4)]
        names=["Fetch","Gray/contrast","Edges (Sobel + closing for source)","Output"]
        lines.append(f"{config}: candidate longest stage is {names[t.index(max(t))]}; sum/max service-time estimate = {sum(t)/max(t):.3f}x. This is a first-order ideal based on measured sequential service times, not a guaranteed upper bound on all real observations.")
        lines.append("")
    lines += ["## Read the supporting measurements", "",
              "- `aggregate.csv`: throughput, latency, stage means, allocation calls, process CPU time and peak memory.",
              "- `comparisons.csv`: paired ratios, intervals and comparison purpose.",
              "- `all_runs.csv`: one row per measured process.",
              "- `experiment.json` resolves raw run paths in the separate baseline/results and pipeline/results directories.",
              "- Each run's `frames.csv`: stage timestamps, source delay and output fingerprints.",
              "- Each run's `workers.csv`: service time, condition-variable waits and worker CPU time.",
              "- Each run's `queues.csv`: time-weighted occupancy and high-water marks.", "",
              "For paced runs, inspect admission_lag_last_ms across runs and frames.csv over time. This source never drops frames; increased virtual-source delay reveals overload. A finite replay does not prove indefinite stream stability.", ""]
    (a.experiment/"analysis.md").write_text("\n".join(lines),encoding="utf-8")

if __name__ == "__main__":
    main()
