# Benchmarking and interpretation

## Treatments

| ID | Execution | Allocation | Traversal | Queue capacity |
| --- | --- | --- | --- | ---: |
| A | Sequential | Per-frame arrays | Row | Not used |
| B | Sequential | Reused slot | Row | Not used |
| C | Four-stage pipeline | Per-frame arrays | Row | 5 |
| D | Four-stage pipeline | Reused slots | Row | 5 |
| E1 | Four-stage pipeline | Reused slots | Row | 2 |
| E3 | Four-stage pipeline | Reused slots | Row | 10 |
| F | Four-stage pipeline | Reused slots | Column | 5 |

D is also E2; there are seven distinct configurations. B/D is primary. A/B tests sequential reuse; C/D tests pipeline reuse; A/C tests dynamic-allocation scheduling; E1/D/E3 tests queues; D/F tests traversal. The pipeline pool remains 34 slots for the queue comparison.

## Protocol

1. Pass correctness and capture checks.
2. Prepare a replay and adjacent JSON manifest. Declare distinct image count and resolution.
3. Run a pilot and select the same frame count for all treatments so the fastest run lasts several seconds; aim for at least ten seconds where practical.
4. Use ten randomized paired blocks with matched build, threshold, input and operators.
5. Disable capture for timing. Record host load, power mode and thermal conditions.
6. Treat each complete run as an observation. Replayed frames do not increase image diversity.
7. Retain valid slow runs. Investigate failed audits rather than interpreting an incomplete experiment.

~~~bash
python scripts/run_review3.py --dataset data/prepared/synthetic_01.epraw --tag primary_01 --frames 600 --repeats 10 --warmup 60
cat results/primary_01/SUMMARY.txt
python scripts/audit_evaluation.py results/primary_01
~~~

Replace 600 with the common frame count selected from a pilot. Add --all-configs for all treatments. A RAM-input control can add --io ram if the replay fits the preload guard. Paced replay uses scripts/benchmark.py with --rates 30 60 and a new output directory directly under results/.

## Result files

| File | Evidence |
| --- | --- |
| results/TAG/SUMMARY.txt | Primary metrics and conclusion |
| results/TAG/aggregate.csv | Per-treatment aggregate fields |
| results/TAG/comparisons.csv | Paired ratios and intervals |
| results/TAG/analysis.md | Interpretation and theory comparison |
| results/TAG/experiment.json | Run order, manifest, commands, build/source identities |
| results/TAG/audit.json | Evaluation integrity checks |
| baseline/results/TAG/runs/ | Sequential raw records |
| pipeline/results/TAG/runs/ | Pipeline raw records |
| frames.csv in each run | Frame order, slots, stage timestamps, latency and fingerprints |
| workers.csv and queues.csv | Actual workers, CPU information, queue occupancy and selected waits |

## Metric definitions

FPS is completed frames divided by timed processing seconds. Paired speedup is the geometric mean of D/B FPS ratios across blocks, not the ratio of displayed median FPS. The analyzer provides a run-level bootstrap 95% interval.

SUMMARY.txt P95/P99 values are medians of per-run admitted-frame percentiles, not a single percentile over pooled frames. CPU 100% means one CPU-equivalent; it can exceed 100% with several workers. Peak RSS is a process high-water measure, including setup.

Stage intervals include preemption. Queue measurements expose selected blocking behavior. They do not measure IPC, cache misses, energy or memory bandwidth.

The ideal large-workload speedup estimate is the sum of sequential stage times divided by the longest stage time. It omits synchronization and contention and does not guarantee 4×.

PNG decoding, input preparation, startup/setup and report rendering are excluded from the timed processing interval. File input includes the OS page cache and is not necessarily physical-disk IO. This is not complete camera-to-recognition latency.

## Historical evidence and limits

The October 24 experiment used six distinct 1920×1080 UFPR-ALPR testing images, 600 replayed frames per run, ten paired B/D blocks and captures disabled. Its paired ratio was 1.520 (95% interval 1.498–1.545), with higher latency and memory. See examples/historical_linux_20261024/.

Older ablations found no pooling throughput benefit in that study and no resolved advantage from larger queues. Those are separate historical experiments, not your fresh results.

These programs do not establish detection/OCR accuracy, production camera loss, indefinite streaming stability, energy savings, optimal threshold or universal speedup.

