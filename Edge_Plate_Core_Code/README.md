# Edge Plate Preprocessor: main native code and architecture

This compact package extracts the native C++ engine from `Review3_Pipeline_Streamlit.zip`. The seven engine source files and `native/build.sh` are copied unchanged. The Streamlit interface, datasets, reference PDFs and historical results are excluded. This package is for examining and running the actual sequential and four-worker implementations.

## Start with these files

| File | What to inspect |
|---|---|
| `engine/baseline/src/main.cpp` | Selects sequential execution with `edge::run(argc, argv, false)` |
| `engine/pipeline/src/main.cpp` | Selects pipelined execution with `edge::run(argc, argv, true)` |
| `engine/shared/src/app.cpp` | Main implementation: input, buffers, four operations, worker creation, execution branches and measurements |
| `engine/shared/include/kernels.hpp` | Exact grayscale, contrast, Sobel, threshold and closing operations |
| `engine/shared/include/queue.hpp` | Bounded FIFO ring of slot IDs, mutex, condition variables, waiting and closure |
| `engine/shared/include/platform.hpp` | Linux / Windows CPU-time and resident-memory measurements |
| `engine/shared/include/app.hpp` | Declaration of the shared `run()` entry point |
| `native/build.sh` | C++20 native build for Linux or MSYS2 UCRT64 |
| `tests/kernels.cpp` | Original kernel tests from the full project; uses the same kernel header |
| `tests/smoke_native.py` | Added integration check using generated RGB input; no third-party Python packages |

The two `main.cpp` files are deliberately small wrappers. The sequential and parallel algorithms are in the shared `app.cpp`, so reading only either wrapper will not explain the architecture.

## Exact preprocessing flow

![Preprocessing flow](docs/preprocessing_flow.png)

For the default `--profile source` path:

1. Fetch decoded RGB bytes from an EPRAW replay file into a slot.
2. Compute integer luminance: `Y = (299*R + 587*G + 114*B + 500) / 1000`.
3. Apply contrast: `gray = clamp((5*Y + 2)/4 - 32, 0, 255)`; divisions are integer divisions.
4. Compute the absolute Sobel Gx response using rows `[-1,0,1]`, `[-2,0,2]`, `[-1,0,1]`.
5. Threshold: values at or above 80 become 255; lower values become 0.
6. Apply full 3-by-3 binary dilation followed by erosion (closing).
7. Copy the final edge map to the output array, calculate fingerprints, store timing records, and recycle the slot.

The Grayscale worker performs steps 2-3. The Edges worker performs steps 4-6. These are not separate native workers. Sobel and final-image border pixels are forced to zero. Closing uses the consumed RGB storage as scratch memory. The separate `sobel()` function implements the optional legacy Gx+Gy profile; it is not the default source-profile path.

The native source is an EPRAW replay, not direct webcam capture or PNG decoding. The existing Streamlit application converts selected images into this replay format before invoking the engines. No detector, OCR or model training is implemented in the native engine.

## Sequential and pipelined scheduling

![Execution architecture](docs/execution_architecture.png)

### Sequential branch

In `app.cpp`, find the final `else` paired with `if(pipeline)`, immediately after the pipeline workers are joined. Its loop contains:

```cpp
fetch(slots[0],id,request); gray(slots[0]); edges(slots[0]); sink(slots[0]);
```

One execution thread completes all four operations for a frame before starting the next. Only one reusable image slot is used, regardless of the `--slots` argument.

### Pipeline branch

In `app.cpp`, find the earlier `if(pipeline)` containing four `launch(...)` calls:

| Worker | Operation and transfer |
|---|---|
| `launch(0, ...)` | Pop free slot, fetch RGB, push slot ID into Q1 |
| `launch(1, ...)` | Pop Q1, compute gray/contrast, push slot ID into Q2 |
| `launch(2, ...)` | Pop Q2, compute Sobel/threshold/closing, push slot ID into Q3 |
| `launch(3, ...)` | Pop Q3, copy output and record result, return slot ID to the free pool |

Defaults are three interstage queues with capacity 5 each and 34 frame slots. Queues move slot identifiers rather than full image arrays. A full queue blocks its producer; an empty queue blocks its consumer. The free pool is a separate queue of available slot IDs. Slots cannot be reused until Output releases them.

Stages may process different frames at overlapping times. Each individual frame still follows Fetch, Gray, Edges and Output in order. This implementation does not split one Sobel image across four workers and does not pin workers to physical cores. Thread failures trigger cancellation and wake blocked participants; normal closure drains admitted work and joins workers.

### Why latency and memory may increase

The Edges stage can limit completion capacity while preceding stages fill queues. Waiting adds to admitted-frame latency. The 34-slot pool allocates more image memory than the sequential one-slot configuration. Reuse avoids repeated allocations; it does not make the pool small. These diagrams explain mechanisms and contain no measured timing or claimed speedup.

## Build and check: Linux primary

Run commands from the extracted `Edge_Plate_Core_Code` directory. A C++20-capable `g++` compiler and Python 3 are required. No Python packages need to be installed for the included smoke check.

```bash
bash native/build.sh
g++ -std=c++20 -O3 -Wall -Wextra -Wpedantic -Iengine/shared/include tests/kernels.cpp -o native/bin/kernel_tests
./native/bin/kernel_tests
python3 tests/smoke_native.py
```

The smoke check generates a temporary 24-by-16 RGB input with three distinct patterns, processes 36 frames per mode, captures the first three frames, and checks completion, stage order, source IDs, slot reuse, queue bounds, worker identity counts and equality of captured planes. Temporary data are removed automatically. Its short runs are correctness checks, not performance measurements.

## Build and check: MSYS2 UCRT64 secondary

Open the **MSYS2 UCRT64** console with its C++ compiler installed. Change to wherever you extracted this package; quote the path if it contains spaces. Then run:

```bash
bash native/build.sh
g++ -std=c++20 -O3 -Wall -Wextra -Wpedantic -Iengine/shared/include tests/kernels.cpp -o native/bin/kernel_tests.exe
./native/bin/kernel_tests.exe
python tests/smoke_native.py
```

If `python` is not available in that shell, use your established Python interpreter, for example `py -3.14 tests/smoke_native.py`. The UCRT64 runtime directory must remain on PATH when launching the native `.exe` files. The build script adds the Windows `psapi` link dependency. Windows execution was not rerun during this extraction.

## Run with an existing prepared dataset

An `.epraw` file is required. A directory of PNG/JPEG images is not a valid `--input` argument. You may reuse an EPRAW file already prepared by the full project or use the existing Streamlit application for ordinary image selection. This compact extraction does not bundle the dataset converter or Streamlit UI.

Linux examples, replacing the input path with an actual prepared file:

```bash
./native/bin/edge_seq --input "/absolute/path/input.epraw" --out results/seq_01 --frames 120 --allocation pool --traversal row --profile source --edge-threshold 80 --capture 3
./native/bin/edge_pipeline --input "/absolute/path/input.epraw" --out results/pipeline_01 --frames 120 --allocation pool --traversal row --profile source --edge-threshold 80 --queue 5 --slots 34 --capture 3
```

Under MSYS2, use the corresponding `.exe` executables and an existing input path. Every output directory must be new; choose a new name on each run. `--frames` repeats source images if it exceeds the source count. Captured frames are included in this total, not additional frames.

Use `--capture 0` for capture-free timing, and repeated paired runs for performance claims. Do not quote the included small smoke-check timings as a benchmark.

## Output files

| File | Meaning |
|---|---|
| `summary.json` | Settings, elapsed time, throughput, latency percentiles, CPU and peak memory |
| `frames.csv` | Frame/source/slot IDs, stage timestamps, latency and fingerprints |
| `workers.csv` | Worker identities, service time, CPU time and queue waiting |
| `queues.csv` | Queue capacity, time-weighted occupancy and observed maximum |
| `captured_gray.raw` | First captured contrast-adjusted grayscale planes |
| `captured_binary.raw` | First captured binary Sobel planes before closing, source profile only |
| `captured_edges.raw` | First captured final closed-edge planes |
| `SUCCESS` | Completion marker written after a successful run |

Raw capture planes are unsigned 8-bit values in row-major order. Each plane contains `width * height` bytes. These files are not PNG images and cannot be opened as ordinary pictures without conversion.

## Scope and provenance

`docs/SOURCE_PROVENANCE.json` records the exact copied engine files and their SHA-256 values. The original project alignment and methodology notes are included for background. Links in those original notes to other full-project files refer to the original package and may not exist in this compact extraction.

The added diagrams are code-grounded architectural illustrations, not measured execution traces. The included source code remains the original implementation. No hardware model is required to use it; hardware details belong to individual measurement records.
