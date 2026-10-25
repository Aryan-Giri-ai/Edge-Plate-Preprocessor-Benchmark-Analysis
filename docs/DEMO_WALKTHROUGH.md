# Fresh local demonstration from the public source ZIP

This is separate from the original academic archive. For its saved traffic-image evidence, see the separately delivered ORIGINAL_ZIP_WALKTHROUGH.md.

## 1. Extract and enter the source root

Download the ZIP and matching checksum to one folder. Once Python/archive tools are installed:

~~~bash
sha256sum -c Edge_Plate_GitHub_Ready.zip.sha256
python3 -m zipfile -t Edge_Plate_GitHub_Ready.zip
python3 -m zipfile -e Edge_Plate_GitHub_Ready.zip EdgePublicDemo
cd EdgePublicDemo/edge-plate-preprocessor
~~~

Use python instead of python3 on MSYS2 if needed. Choose a new extraction destination. Follow SETUP.md for dependencies, virtual-environment activation on Linux and builds. The public ZIP regenerates demos and includes no UFPR images.

## 2. Build and check

~~~bash
bash scripts/build.sh
python scripts/check.py --report evidence/demo_correctness.json
python tests/check_capture.py
python tests/check_prepare_groups.py
~~~

Resolve any error before presenting the run.

## 3. Demonstrate without a dataset download

~~~bash
python scripts/prepare_data.py synthetic --width 640 --height 360 --count 6 --out data/prepared/synthetic_01.epraw
python scripts/review3_demo.py --dataset data/prepared/synthetic_01.epraw --out results/demo_01 --frames 120 --capture 3
cat results/demo_01/console.txt
python scripts/open_viewer.py results/demo_01/index.html
~~~

This checks the workflow on generated patterns; it is not traffic-camera evidence.

## 4. Demonstrate authorized traffic images

For a single-resolution image folder:

~~~bash
python scripts/prepare_data.py images --input "/path/to/authorized/images" --limit 6 --out data/prepared/real_01.epraw
python scripts/review3_demo.py --dataset data/prepared/real_01.epraw --out results/real_demo_01 --frames 120 --capture 3
python scripts/open_viewer.py results/real_demo_01/index.html
~~~

Selection is deterministic over sorted relative paths. Inspect the adjacent replay .json to establish exactly what was selected. Point at testing/ for a UFPR test sample; the programs do not train.

For a mixed-resolution collection:

~~~bash
python scripts/prepare_image_groups.py --input "/path/to/UFPR/testing" --out data/prepared/test_groups_01 --limit 6
cat data/prepared/test_groups_01/groups.json
~~~

Read each listed replay name, then use it as --dataset in the demo and benchmark commands. For example, use data/prepared/test_groups_01/1920x1080.epraw if that file is listed. Use --limit 0 for all supported images after checking disk capacity.

Evaluate every group if claiming coverage of the selected collection. The preparation tool preserves dimensions and does not calculate a combined stream FPS.

## 5. Display and explain

First display console.txt. A and B each record one execution thread; D records four workers. Open the HTML viewer:

1. Select B and explain sequential stage intervals.
2. Select D and show different frames overlapping across workers.
3. Move the captured-frame and timeline controls.
4. Show RGB, grayscale/contrast, binary Sobel, final closed edges and closing-change pixels.
5. Show the B–D difference: black means matching captured pixels.
6. Read the byte-equality and slot-order checks.

The viewer presents recorded output from the execution you just ran. Worker IDs are not CPU core IDs. W3 performs the complete edge stage for a frame. Morphological closing changes the binary map; threading preserves the defined result.

## 6. Benchmark separately

~~~bash
python scripts/run_review3.py --dataset data/prepared/real_01.epraw --tag local_primary_01 --frames 600 --repeats 10 --warmup 60
cat results/local_primary_01/SUMMARY.txt
python scripts/audit_evaluation.py results/local_primary_01
~~~

Use your prepared replay and a common frame count selected from a pilot. Captures are disabled by the wrapper. Run the benchmark before the meeting and present its summary/audit during the meeting.

~~~bash
python scripts/run_review3.py --dataset data/prepared/real_01.epraw --tag local_ablations_01 --frames 600 --repeats 10 --warmup 60 --all-configs
cat results/local_ablations_01/SUMMARY.txt
~~~

Use fresh tags. For mixed resolutions, benchmark each group separately with a distinct tag and report each group's coverage.

## 7. Result interpretation

Compare FPS, paired ratio/interval, P95/P99 latency, CPU use and peak memory. Show frame/worker/queue records for order, ownership and waits. Retain slowdowns and inconclusive results.

Keep historical Linux figures separate from newly measured results. Output equality is not plate-detection or OCR accuracy. A theoretical upper-model speedup is not a measured outcome.

## 8. Meeting sequence

| Display | Explain |
| --- | --- |
| Source folders | Separate entry points, shared kernels |
| B output and timeline | Sequential reference |
| D output and timeline | Four stages and bounded ownership |
| Binary, closed and difference maps | Morphological effect and B/D equality |
| Fresh summary and audit | Throughput, latency and memory |
| Ablation table | Allocation, queues and traversal |
| Limitations | Tested host/data, no detector/OCR or hardware counters |

The combined speaking script is MENTOR_SCRIPT_REVIEW2_REVIEW3.md.

