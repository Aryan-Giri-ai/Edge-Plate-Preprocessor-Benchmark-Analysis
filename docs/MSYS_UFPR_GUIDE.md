# MSYS2 guide: initialize and assess UFPR-ALPR

## 1. Extract the head project folder

From the folder containing the ZIP and its checksum file, verify the download first:

```bash
sha256sum -c Edge_Plate_UFPR_Project.zip.sha256
python -m zipfile -t Edge_Plate_UFPR_Project.zip
```

Both checks must pass. Then extract the new ZIP into a fresh location. Keep the root `Edge_Plate_UFPR_Project` folder and every subdirectory together. Example:

`E:\myCAO catalog\projects\Repository\Edge_Plate_UFPR_Project`

Open **MSYS2 UCRT64**. Use your existing GCC/Python installation. If these dependencies are missing:

```bash
pacman -Syu
pacman -S --needed mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-python mingw-w64-ucrt-x86_64-python-pillow
```

Follow a requested MSYS2 restart before continuing updates. Confirm:

```bash
echo "$MSYSTEM"
which g++
which python
python -c "from PIL import Image; print('Pillow available')"
cd "/e/myCAO catalog/projects/Repository/Edge_Plate_UFPR_Project"
python scripts/check_package.py
```

MSYSTEM must be UCRT64. Directory examples describe extraction choices, not paths inspected on your PC.

Official setup references, checked 2026-10-02: [MSYS2 full system updates](https://www.msys2.org/docs/updating/), [UCRT64 GCC](https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-gcc), [UCRT64 Python](https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-python), [UCRT64 Pillow](https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-python-pillow).

## 2. Point the project at the installed data

The verified Drive dataset is at:

https://drive.google.com/drive/folders/1qDhsc30Td6qPn6gKIC9vv6vtrDGvFBzi

Its parent organization is `Project Directory/dataset/UFPR-ALPR dataset`. This web location does not reveal your local Windows drive letter. If the dataset is already downloaded or available offline through Drive for desktop, use that existing folder. Otherwise download the dataset folder from Drive and extract it locally. The selected folder must directly contain `training`, `validation`, `testing` and the dataset README.

For example, if Explorer shows `C:\datasets\UFPR-ALPR dataset`, use:

```bash
ls "/c/datasets/UFPR-ALPR dataset"
ls "/c/datasets/UFPR-ALPR dataset/training/track0001"
```

If you use a Drive-for-desktop path, substitute its actual path. Make files available offline before timing: network hydration during preprocessing or replay preparation can fail or distort elapsed process time. Benchmark runs use the locally prepared EPRAW files.

## 3. Build the two programs

Build both:

```bash
bash scripts/build.sh
```

Or build them separately:

```bash
bash baseline/build.sh
bash pipeline/build.sh
```

The resulting programs are:

- `baseline/build/edge_seq.exe`
- `pipeline/build/edge_pipeline.exe`

Both builds use the same C++20, `-O3 -DNDEBUG -pthread` flags and the same shared code. Build both again after changing anything under shared/. Root `build/` holds the common object, kernel tests and build metadata; it is not the program-results directory.

```bash
python scripts/check.py --report evidence/windows_correctness.json
```

Continue only after the correctness command succeeds. It checks all seven configurations, both available profiles, independent small-image reference bytes, queue stress and cancellation behavior.

## 4. Initialize baseline and pipeline together

For a practical first run:

```bash
python scripts/initialize.py --dataset-root "/c/datasets/UFPR-ALPR dataset" --run-name ufpr_init --limit-per-split 60 --capture 4
```

This command:

1. Checks local split counts, track separation, file pairing, 1920×1080 PNG headers and annotation geometry.
2. Selects up to 60 images in each split, spreading selection across tracks before taking extra frames from a track. It preserves split membership.
3. Decodes selected PNGs into shared RGB replay inputs, without resizing or cropping, and stores source/annotation/replay hashes.
4. Runs sequential B and pooled pipeline D using identical configuration and source order.
5. Writes results into `baseline/results/ufpr_init/<split>` and `pipeline/results/ufpr_init/<split>`.
6. Checks complete captured grayscale/edge bytes and fingerprints across every processed frame. It writes comparisons under `results/ufpr_init/<split>`.

Prepared files are in `data/prepared/ufpr_init`. Output destinations are exclusive: choose a new run name for a new initialization. A failed/incomplete preparation has no completed audit; a failed assessment has no `ASSESSMENT_SUCCESS` marker. Do not analyze incomplete runs.

The initializer expects the complete official source inventory by default. For a deliberately partial local sample, add `--allow-partial`; the report records this status. Do not use that option to hide a failed or incomplete dataset download.

**Training meaning:** no fitting occurs. Grayscale, Sobel, threshold 80 and closing are fixed operations. The official training split is used for initial execution and timing pilots; validation is available for checking the frozen setup; testing is available for the final preselected comparison. No SVM or neural network has been trained.

## 5. Prepare all data, or rerun one program

Prepare the full installed dataset without immediately running programs:

```bash
python scripts/prepare_ufpr.py --dataset-root "/c/datasets/UFPR-ALPR dataset" --out data/prepared/full --limit-per-split 0
```

Decoded RGB storage is approximately 10.43 GiB for training, 5.21 GiB for validation and 10.43 GiB for testing, totaling 26.07 GiB, in addition to the original PNGs, output files and OS space. The installed PNG metadata totals about 10.73 GB. Use file mode for a full partition; the program's RAM preload limit is 1 GiB. Preparation checks free disk space before allocating the replay files.

Run only the baseline on prepared data:

```bash
python baseline/run.py --prepared data/prepared/ufpr_init --split training --run-name baseline_trial --config B --capture 4
```

Run only the pipeline:

```bash
python pipeline/run.py --prepared data/prepared/ufpr_init --split training --run-name pipeline_trial --config D --capture 4
```

Compare those runs:

```bash
python scripts/compare_runs.py --baseline baseline/results/baseline_trial/training --pipeline pipeline/results/pipeline_trial/training --out results/manual_comparison
```

The comparison rejects differing split, dataset/manifest hash, frame count, profile, threshold, IO, traversal or allocation settings. B/D is the primary matched pair; use benchmark.py for the full ablations that deliberately change one factor.

Native executable example, with explicit controls:

```bash
./baseline/build/edge_seq.exe --input data/prepared/ufpr_init/training.epraw --out baseline/results/native_B --frames 120 --allocation pool --traversal row --profile source --edge-threshold 80 --io file
./pipeline/build/edge_pipeline.exe --input data/prepared/ufpr_init/training.epraw --out pipeline/results/native_D --frames 120 --allocation pool --traversal row --queue 5 --slots 34 --profile source --edge-threshold 80 --io file
```

A larger frame count replays the selected source cyclically. It does not create additional distinct images. Native commands write core measurements; the Python project launchers additionally generate context, annotation diagnostics and HTML/PNG outputs.

## 6. Display actual results and thread parallelization

Open the generated baseline and pipeline output pages:

```bash
python -c "import os; os.startfile(os.path.abspath('baseline/results/ufpr_init/training/outputs.html'))"
python -c "import os; os.startfile(os.path.abspath('pipeline/results/ufpr_init/training/outputs.html'))"
```

Each captured frame provides the original RGB input, actual grayscale/contrast output, actual closed edge map and a crop of that edge map using the **supplied ground-truth annotation**. The crop is an inspection aid. It is not a detected plate or predicted bounding box.

`output_diagnostics.csv` records nonzero-edge fractions for the whole image, the annotation-derived plate bounding box and its complement. These are descriptive edge occupancies. They do not measure recognition accuracy, IoU, precision, recall or a trained loss.

Run the interactive measured-timeline demo:

```bash
python scripts/demo.py --dataset data/prepared/ufpr_init/training.epraw --out results/live_demo --frames 120 --capture 4
python -c "import os; os.startfile(os.path.abspath('results/live_demo/index.html'))"
```

This runs A/B/D, checks captured output equality, and displays recorded worker IDs, per-frame intervals, slot reuse, queues, waits and metrics. Native demo runs remain separated under baseline/results/live_demo and pipeline/results/live_demo. The combined viewer is in results/live_demo. Full image captures add copying and are excluded from the primary timing study.

Threads overlap different frames. A Sobel image is not spatially divided among four workers. Wall-interval overlap is observable, but it includes possible preemption; it is not proof that four cores simultaneously retired instructions. The OS chooses worker placement.

## 7. Start the complete comparative experiment

Use the training replay for the duration pilot:

```bash
python scripts/benchmark.py --dataset data/prepared/ufpr_init/training.epraw --out results/ufpr_pilot --frames 300 --repeats 3 --warmup 60 --rates 0 --slots 34
```

All A, B, C, D/E2, E1, E3 and F configurations run in randomized blocks. Sequential raw runs go under baseline/results/ufpr_pilot; pipeline raw runs go under pipeline/results/ufpr_pilot. Combined metadata, aggregate CSVs and analysis are in results/ufpr_pilot. Keep these directories together; experiment.json uses relative cross-directory paths.

| Pair | Effect examined |
|:---|:---|
| B/A | Sequential buffer reuse |
| C/A | Pipeline with dynamic arrays |
| D/B | Primary pipeline comparison with reuse in both |
| D/C | Pooling within the pipeline |
| D/E1 and E3/D | Queue depths 2, 5 and 10 with 34 slots held fixed |
| D/F | Row versus column traversal |
| D/A | Combined change, not isolated threading benefit |

Choose a frame count giving sufficiently long runs on your laptop. Then use the frozen settings and test partition, for example:

```bash
python scripts/benchmark.py --dataset data/prepared/full/testing.epraw --out results/ufpr_final --frames 3600 --repeats 10 --warmup 120 --rates 0 --slots 34 --io file
```

3600 is an example, not an established optimal duration. Use one common count for every configuration. Run benchmarks alone, with consistent power/cooling/background conditions. Ten blocks supply repeated evidence; short included smoke tests do not.

Paced behavior is a separate experiment:

```bash
python scripts/benchmark.py --dataset data/prepared/ufpr_init/testing.epraw --out results/ufpr_paced --configs B D E1 E3 --frames 1800 --repeats 5 --warmup 60 --rates 30 60 --slots 34 --io file
```

The source blocks and preserves order. Inspect scheduled-source latency and admission lag; zero reported dropped frames does not prove live-camera capacity. Evaluate FPS, paired speedup and confidence interval, P50/P95/P99 latency, stage service times, queue occupancy, CV waits, CPU seconds, allocation counts and peak process memory. Hardware IPC/cache counters require external profiling and are not fabricated by these scripts.

Read [COMPARATIVE_ANALYSIS.md](COMPARATIVE_ANALYSIS.md) for interpretation, uncertainty and theoretical stage-balance limits. Theory does not guarantee a favorable result. Report slowdowns and latency/memory increases as measured.

## 8. What has already been initialized

The included run evidence is from **18 real full-resolution images** retrieved from your Drive: six per official split, from three tracks per split. All 18 captured gray and edge outputs matched between baseline B and pipeline D. A further A/B/D timeline demo replays the six selected training images, and the complete seven-configuration runner receives a short two-block smoke test.

The later Review 2 evaluation adds a ten-block, seven-configuration test-image replay study, plus paced and RAM controls. Read [REVIEW2_EVALUATION.md](REVIEW2_EVALUATION.md) for measured results and limits. These are Linux sample measurements. They are not a completed 4,500-image experiment, Windows performance study or trained recognition model. The full dataset, decoded replays, binaries and large initialization image/raw captures are excluded from the project download. The compact real-output contact sheet, measured logs and two captured frames in results/thread_demo are included. Running the commands above recreates the full-resolution PNG outputs on your installed data.

## 9. Audit and present the comparison

Recompute an included result without the private input replay or compiled binaries:

```bash
python scripts/analyze.py results/review2_evaluation
python scripts/audit_evaluation.py results/review2_evaluation
cat results/review2_evaluation/analysis.md
```

After your own final experiment, substitute results/ufpr_final in these commands. The audit rejects missing blocks/configurations, mismatched output fingerprints, invalid frame or slot order, unexpected allocation settings, captures in timing runs, and queue-bound violations. The analysis uses one process run as an observation; individual correlated replay frames are not statistical replicates.

For Review 2, use this order:

1. State the source-aligned preprocessing scope and show SOURCE_ALIGNMENT.md.
2. Run the correctness check and show the passed report.
3. Run initialization and open both outputs.html pages; explain annotation crops are ground truth.
4. Open the measured timeline demo and select A, B, D to show frame order, worker overlap and slot reuse.
5. Show the precomputed repeated benchmark, audit.json, aggregate.csv and comparisons.csv. Do not use a captured demo's FPS as the primary timing result.
6. Explain D/B first, then allocation, queue and traversal ablations. Show adverse latency or memory results alongside throughput.
7. End with limitations and the remaining Windows/full-dataset validation. The included Review 2 draft supplies defensible wording; replace its Linux numbers only with your own recorded results.
