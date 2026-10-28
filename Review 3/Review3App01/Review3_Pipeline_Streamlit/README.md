# Review 3 native pipeline application

This is a separate Streamlit application for the Review 3 demonstration. It keeps the Review 2 image panels and adds actual native pipeline execution, a measured thread timeline, event replay, frame routing, queue records, output agreement and an optional capture-free paired comparison.

Four persistent C++ workers process different frames: W1 Fetch → W2 Gray/contrast → W3 Sobel/threshold/closing → W4 Output/recycle. Within one frame the stages remain ordered; across frames they can overlap. The app does not simulate threads or split one Sobel image across four workers.

## 1 Separate Windows folder

Save Review3_Pipeline_Streamlit.zip in:

E:\myCAO catalog\Review 3

The extraction below creates:

E:\myCAO catalog\Review 3\Review3App01\Review3_Pipeline_Streamlit

Your Review 2 application remains under Review 2. Use port 8502 for Review 3 so both applications can be opened separately.

## 2 Extract and create the environment

Use VS Code PowerShell. Your working standard Windows interpreter was E:\Python\python.exe (Python 3.14); use that directly rather than the stale Python 3.12 launcher entry.

Create the Review 3 directory if needed, then place the downloaded ZIP there. Run:

~~~powershell
Set-Location "E:\myCAO catalog\Review 3"
Expand-Archive -LiteralPath ".\Review3_Pipeline_Streamlit.zip" -DestinationPath ".\Review3App01"
Set-Location ".\Review3App01\Review3_Pipeline_Streamlit"
& "E:\Python\python.exe" -m venv .venv314
& ".\.venv314\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv314\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv314\Scripts\python.exe" -c "import streamlit, numpy, PIL, altair, pandas; print('Review 3 dependencies ready')"
~~~

Use a fresh extraction destination if Review3App01 exists. Python 3.14 is your selected environment; it is not a hardware-specific requirement.

## 3 Open VS Code

File → Open Folder:

E:\myCAO catalog\Review 3\Review3App01\Review3_Pipeline_Streamlit

Install Microsoft's Python extension if needed. Press Ctrl+Shift+P → Python: Select Interpreter → Enter interpreter path. Select this project's .venv314\Scripts\python.exe.

Use the Python environment in this folder. The native C++ executables are built separately through MSYS2.

## 4 Build both native engines

Native execution is required to show real thread evidence. Open MSYS2 UCRT64 and run:

~~~bash
cd "/e/myCAO catalog/Review 3/Review3App01/Review3_Pipeline_Streamlit"
bash native/build.sh
ls native/bin/edge_seq.exe native/bin/edge_pipeline.exe
~~~

The build uses the same shared kernels and runtime for both programs. The supplied engine source is copied unchanged from the verified GitHub-ready project. B is sequential with reuse; D is the pipeline with reuse, row traversal and 34 slots.

If a compiler/runtime dependency error occurs, resolve the MSYS2 full upgrade before building. Do not bypass dependency checks.

## 5 Launch Review 3 from VS Code PowerShell

~~~powershell
Set-Location "E:\myCAO catalog\Review 3\Review3App01\Review3_Pipeline_Streamlit"
$env:PATH = "E:\msys64\main file\ucrt64\bin;" + $env:PATH
& ".\.venv314\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
~~~

Open http://127.0.0.1:8502. Keep the terminal running. Stop with Ctrl+C. Add the UCRT64 bin directory in each new launch terminal so the native Windows executables find their DLLs. Use your actual installation location if it differs from the confirmed E:\msys64\main file.

Do not use Run Python File on app.py. Start it through Streamlit.

## 6 First pipeline test

1. Select Generated sequence.
2. Keep Replayed frames = 120, Captured frames = 3, threshold = 80 and queue = 5.
3. Press Run baseline and native pipeline.
4. Wait for actual B and D executions and their correctness checks.
5. Confirm one B thread identity and four D worker identities.

Generated inputs are synthetic and labeled as such. The example creates six distinct shifted patterns. Replaying 120 frames does not create 120 distinct source images.

Processing begins only after submitting Run. A failed native run or mismatched captured output is rejected. There is no Python-only fallback that imitates native concurrency.

## 7 Use the installed UFPR images

The local-folder field defaults to your confirmed location:

E:\NEW DOWNLOADS\VIT Downloads\Other Downloads\Assignments

Choose Local dataset → Find images → select 1 to 12 source images. Prefer the actual UFPR testing subfolder, or a single test track, for a focused presentation.

All selected images must share their original dimensions. The app rejects mixed sizes rather than resizing. Choose a common resolution group if the installation contains both 1920×1080 and 1920×1088 images. Image limit: 4 megapixels per source and 8192 pixels per side.

Alternatively upload several authorized images using Upload images. Original source files are not changed. No dataset is bundled or automatically downloaded.

## 8 Show parallel and consecutive execution

### A Measured thread timeline

Select D — Pipeline. Each colored bar is an actual stage service interval from frames.csv. Colors identify frame IDs. Choose the first frame in the timeline to inspect different windows; up to 12 frames are shown at once.

The rows are W1 Fetch, W2 Gray/contrast, W3 Sobel/threshold/closing and W4 Output/recycle. Bars for different frames can overlap. The worker table displays actual thread IDs and CPU/wait information.

Switch to B — Sequential. Its four stage rows share one thread identity and the recorded intervals do not overlap.

The red timeline rule, when within the displayed window, marks the selected replay time. Native runs have separate time origins and scales. Do not compare their bar lengths as if they were aligned concurrent executions.

### B Recorded event replay

Use Next event, Previous event, Reset replay or the Recorded event index slider. Each step selects the next actual stage-begin or stage-end timestamp. The table shows the frame in recorded service on each worker at that instant.

This is deterministic playback after execution, not live observation of CPU cores. A row with No service interval does not prove whether the worker was waiting, preempted or performing uninstrumented bookkeeping.

A peak wall-interval overlap greater than one supports stage overlap. It does not establish simultaneous instruction execution on dedicated CPU cores. The OS schedules the workers and no core affinity is enforced.

### C One frame's consecutive route

Choose a captured frame. The This frame through consecutive workers table shows its W1 → W2 → W3 → W4 begin/end times, thread identities and slot. Its stage order is sequential even when other frames are active.

W3 processes the whole Sobel, threshold and closing stage for each frame. No pixel tiling or intra-Sobel multithreading is implemented.

## 9 Show actual image results

For each captured frame, show:

- Original RGB and integer grayscale.
- Captured contrast grayscale.
- Vertical Sobel response preview.
- Captured binary Sobel before closing.
- Captured pipeline closed edges.
- Captured sequential closed edges.
- B–D difference and closing-change maps.

The contrast grayscale, binary map and final edge map come from actual native captures. Raw grayscale and the fixed 0–1020 Sobel-strength preview are Python diagnostic views. No algorithm changes are hidden by the viewer.

Captured B/D planes must match byte for byte and match the Python equivalent. Every replayed frame also has matching source-index, sum and weighted-sum fingerprints. Those fingerprints are not cryptographic proof of byte equality for uncaptured frames.

The source profile uses weighted integer grayscale, fixed contrast, absolute Gx, threshold 80 by default, and full 3×3 dilation followed by erosion. Borders follow the existing zero policy. Threshold changes are exploratory and are recorded with the run.

Closing changes the edge representation. More threads do not improve the numerical edge map. There is no model training, plate detector or OCR accuracy measurement.

## 10 Optional paired performance comparison

The first table is labeled Demonstration measurements because capture is enabled. Do not use that run for the primary speedup claim.

Open Optional capture-free paired benchmark. It uses the images, threshold and queue settings of the completed demo, not unsent changes in the input controls.

1. Choose timed frames per process, paired blocks and warmup frames.
2. Start with 3 blocks as a pilot.
3. Increase the common frame count if the fastest run is too short; aim for several seconds and preferably around ten seconds.
4. Use 10 paired blocks for the planned evaluation.
5. Press Run capture-free comparison.
6. Inspect paired geometric D/B throughput, its run-level bootstrap interval, P95 latency and memory for every run.

B/D order is randomized inside each block using a fixed seed. Warmup is a separate unpaced process. Capture is zero during timing. Inputs and numerical settings match. Raw frame, worker and queue records are retained in the download. All-frame fingerprints and structural trace checks must pass.

Run-to-run intervals do not establish dataset or hardware generalization. A speedup is not guaranteed. Short runs or fewer than ten blocks are explicitly labeled exploratory. Keep slow but valid results.

The existing full seven-treatment A–F ablation workflow remains in the separate project. This GUI compares B/D and lets queue depth vary between complete experiments; it does not automatically run the full ablation matrix.

## 11 Download and preserve evidence

Press Download captures and execution records. The ZIP contains:

- demo.json: run settings, summaries, traces, audits and source identities.
- B/ and D/ frame, worker and queue CSVs.
- images/: actual source/capture/diagnostic maps.
- benchmark.json when a capture-free comparison has completed.

The source directory and images remain local. Native replay/output folders are temporary and removed after loading the records. Download the evidence before closing the session if you need to preserve it. Generated records can contain selected local source paths; review them before public sharing.

## 12 Run validation

In the VS Code PowerShell terminal:

~~~powershell
$env:PATH = "E:\msys64\main file\ucrt64\bin;" + $env:PATH
& ".\.venv314\Scripts\python.exe" tests/check_app.py
~~~

Native engines must already be built. The test suite checks small/border cases, thresholds 0/80/1020, 1920×1080 capture equality, real overlap, rejection of damaged traces, frame replay, evidence export and the Streamlit controls.

The new application was tested on Linux with generated inputs. Native Windows execution and your real UFPR timings must be checked on your system.

## 13 Linux

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
bash native/build.sh
python tests/check_app.py
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
~~~

No processor model or fixed RAM requirement is imposed. Feasible image, slot and capture sizes depend on available resources.

## 14 Troubleshooting

| Symptom | Action |
| --- | --- |
| Run is disabled | Build both native executables in native/bin |
| DLL / native startup failure | Add the actual UCRT64 bin directory to launch-terminal PATH |
| Missing Python modules | Install requirements with this folder's .venv314 executable |
| Mixed-resolution input rejected | Choose same-size source images; original files are not resized |
| Few overlapping intervals | Inspect recorded events and host resources; overlap is measured, not forced |
| Trace says one thread | Check whether B — Sequential is selected |
| Source images changed but results did not | Submit Run again; prior completed results remain labeled |
| Missing images after session ends | Download evidence while the completed result is still in session |
| Port occupied | Use 8503 in the command and open that port |

## Sources and boundaries

The original C++ source is unchanged. Chen et al., Procedia Computer Science 243 (2024), Sections 4.4.1–4.4.2, supports Sobel/threshold/closing. US6553131B1 Fig. 1 block 16 supports vertical-edge extraction, without specifying Sobel. Numerical constants and border rules are project choices.

- Article: https://doi.org/10.1016/j.procs.2024.09.149
- Patent: https://patents.google.com/patent/US6553131B1/en
- Dataset access: https://github.com/raysonlaroca/ufpr-alpr-dataset
- Streamlit: https://docs.streamlit.io/get-started/installation/command-line
- VS Code: https://code.visualstudio.com/docs/python/environments

The MIT license applies to project code. Dependencies and UFPR data retain their own terms. No source dataset images, annotations, compiled binaries or reference PDFs are included.

