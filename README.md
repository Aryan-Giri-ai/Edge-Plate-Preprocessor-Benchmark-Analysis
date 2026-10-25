# Edge Plate Preprocessor

A CPU-based C++20 image preprocessor with separate sequential and four-stage pipeline implementations, shared numerical kernels, recorded thread demonstrations and paired benchmarking.

**Linux is the primary environment; Windows through MSYS2 UCRT64 is secondary.** The application has no processor-model restriction, fixed RAM requirement or GPU dependency. Feasible image sizes and buffer counts depend on available resources; performance is measured on the host where it runs.

The transform is RGB → grayscale/contrast → vertical Sobel → binary threshold → 3×3 morphological closing → output. There is no training step, plate detector or OCR recognizer.

## Documentation

| File | Purpose |
| --- | --- |
| [SETUP.md](docs/SETUP.md) | Linux-first dependencies and builds, followed by MSYS2 |
| [GITHUB_PUBLISH.md](docs/GITHUB_PUBLISH.md) | Repository root, included files and push commands |
| [DEMO_WALKTHROUGH.md](docs/DEMO_WALKTHROUGH.md) | Fresh local demo, image viewer and results presentation |
| [BENCHMARKING.md](docs/BENCHMARKING.md) | Metrics, ablations and interpretation |
| [METHODOLOGY.md](docs/METHODOLOGY.md) | Exact operators, allocation policy and timing boundaries |
| [SOURCE_ALIGNMENT.md](docs/SOURCE_ALIGNMENT.md) | Relationship to the paper and patent |
| [MENTOR_SCRIPT_REVIEW2_REVIEW3.md](docs/MENTOR_SCRIPT_REVIEW2_REVIEW3.md) | Combined review speaking script |
| [THIRD_PARTY.md](THIRD_PARTY.md) | Dataset, reference-document and dependency boundaries |

## Linux quick start

After installing the system packages in docs/SETUP.md, run from this root:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
bash scripts/build.sh
python scripts/check.py --report evidence/local_correctness.json
python tests/check_capture.py
python tests/check_prepare_groups.py
python scripts/prepare_data.py synthetic --width 640 --height 360 --count 6 --out data/prepared/synthetic_01.epraw
python scripts/review3_demo.py --dataset data/prepared/synthetic_01.epraw --out results/demo_01 --frames 120 --capture 3
python scripts/open_viewer.py results/demo_01/index.html
~~~

This demonstrates execution and output agreement using generated patterns. Use authorized traffic images for a traffic-data study. The browser is outside the timed workload.

~~~bash
python scripts/run_review3.py --dataset data/prepared/synthetic_01.epraw --tag pilot_01 --frames 600 --repeats 3 --warmup 60
cat results/pilot_01/SUMMARY.txt
~~~

The small synthetic command is a workflow pilot. Select a common frame count that gives sufficiently long runs on your host, then use ten repeats for the planned study. Use fresh names for subsequent runs.

## Directory framework

| Directory | Responsibility |
| --- | --- |
| baseline/src/ | Sequential entry point |
| pipeline/src/ | Pipeline entry point |
| shared/include/ and shared/src/ | Kernels, queues, platform metrics and runtime |
| scripts/ | Build, preparation, demo, benchmarks and audits |
| tests/ | Independent numerical, capture and preparation checks |
| config/ | Recorded algorithm settings |
| data/ | Local generated or authorized input, ignored except its README |
| baseline/results/ and pipeline/results/ | Separate native records, ignored by Git |
| results/ | Joint comparisons and HTML demos, ignored by Git |
| evidence/ | Local checks, ignored by Git |
| examples/historical_linux_20261024/ | Labeled historical aggregate tables; no dataset images |
| docs/ | Setup, methods, demo and publishing instructions |
| .github/workflows/ | Linux CI configuration; smoke checks are not performance evidence |

Push this entire root folder, with README.md, CMakeLists.txt, baseline/, pipeline/ and shared/ as siblings. Read docs/GITHUB_PUBLISH.md.

## Architecture and evidence

B processes one frame completely before the next, reusing a slot. D overlaps four stages on different frames using bounded queues and 34 pooled slots. Four workers do not divide one Sobel image into four parts.

Seven configurations isolate scheduling, allocation policy, queue capacities 2/5/10 and traversal order. Captured outputs must agree before speed is interpreted. The visual demo enables captures; the benchmark wrapper disables them.

The historical six-image Linux study in examples/ measured a paired throughput ratio of 1.520, alongside higher latency and memory. Those figures describe that experiment, not a guarantee. New measurements belong to the host, dataset and protocol that produced them.

## License

Original project software is provided under the MIT license. Dataset and third-party rights are separate; see THIRD_PARTY.md.

