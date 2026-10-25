# Setup: Linux primary, MSYS2 secondary

Run commands from the repository root unless instructed otherwise. Requirements are Bash, a C++20 compiler, Python 3.10 or newer and Pillow for image conversion and the viewer. GCC 13.3 was used for the saved Linux study; other toolchains must pass the checks.

No processor model, fixed memory size, CUDA toolkit, OpenCV installation or learning framework is required. The pipeline creates four software workers; the scheduler chooses where they execute. Fewer available CPU resources can reduce or eliminate a speed benefit.

## 1. Linux: Ubuntu/Debian example

~~~bash
sudo apt update
sudo apt install -y build-essential python3 python3-venv python3-pip git unzip
~~~

These commands target Debian-based distributions. On other Linux distributions, install equivalent compiler, Bash, Python, virtual-environment, Git and archive tools with your package manager.

Enter your extracted folder:

~~~bash
cd "$HOME/projects/edge-plate-preprocessor"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
g++ --version
python --version
python -c "from PIL import Image; print('Pillow ready')"
~~~

Activate .venv in each new terminal before using python commands.

### Build and validate

~~~bash
bash scripts/build.sh
python scripts/check.py --report evidence/local_correctness.json
python tests/check_capture.py
python tests/check_prepare_groups.py
~~~

Build outputs: baseline/build/edge_seq, pipeline/build/edge_pipeline and build/kernel_tests. The suite tests all seven configurations, numerical borders, malformed input, queue pressure and failure handling.

Separate builds:

~~~bash
bash baseline/build.sh
bash pipeline/build.sh
~~~

Optional CMake build after installing cmake (the Bash build is the verified path in this release):

~~~bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
~~~

CMake places the two executables in their family build directories. Keep build flags matched when comparing scheduling.

### First demo

~~~bash
python scripts/prepare_data.py synthetic --width 640 --height 360 --count 6 --out data/prepared/synthetic_01.epraw
python scripts/review3_demo.py --dataset data/prepared/synthetic_01.epraw --out results/demo_01 --frames 120 --capture 3
cat results/demo_01/console.txt
python scripts/open_viewer.py results/demo_01/index.html
~~~

On headless Linux, copy the complete demo directory to a computer with a browser. Keep images/ beside index.html. No browser is required for preprocessing or benchmarking.

## 2. Windows: MSYS2 UCRT64

Install MSYS2 from https://www.msys2.org/ and open MSYS2 UCRT64. Update fully:

~~~bash
pacman -Syu
~~~

If instructed to close terminals, close them, reopen UCRT64 and repeat until the update finishes.

~~~bash
pacman -S --needed git unzip mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-python mingw-w64-ucrt-x86_64-python-pillow
echo "$MSYSTEM"
which g++
which python
python -c "from PIL import Image; print('Pillow ready')"
~~~

Expect UCRT64 and tools under /ucrt64/bin. Use the pacman Pillow package; the Linux virtual-environment steps are not required.

~~~bash
cd "/e/myCAO catalog/projects/Repository/edge-plate-preprocessor"
bash scripts/build.sh
python scripts/check.py --report evidence/windows_correctness.json
python tests/check_capture.py
python tests/check_prepare_groups.py
~~~

Use your actual path. Family binaries end in .exe. The same demo and benchmark Python commands work after setup. The build links Windows process-metric support automatically.

~~~bash
python scripts/open_viewer.py results/demo_01/index.html
~~~

## 3. Resource planning

An RGB replay requires 20 + 3WHN bytes for N distinct source frames. Pipeline frame arrays plus the output buffer require approximately (5S + 1)WH bytes for S slots, before runtime, logs, capture and allocator overhead. At 1920×1080 and 34 slots, that array estimate is about 338 MiB.

The benchmark wrapper fixes 34 slots for matched ablations. These are experimental controls, not optimal-resource settings. Use smaller synthetic dimensions for a low-resource workflow check. File input supports collections larger than RAM; RAM preload has a 1 GiB guard. Use three captured frames for a compact demo and capture disabled for performance.

## 4. Troubleshooting

| Symptom | Action |
| --- | --- |
| g++ missing | Install a compiler; on Windows verify UCRT64 |
| PIL missing | Linux: activate .venv and install requirements; UCRT64: install python-pillow |
| Output exists | Use fresh input/output names and benchmark tags |
| Dimension mismatch | Use scripts/prepare_image_groups.py |
| Missing .json | Keep the replay and adjacent manifest together |
| Benchmark rejected | Read the first error and raw logs before presenting results |
| Browser not launched | Open the printed absolute HTML path manually |
| Slower pipeline | Retain the result; inspect service times, waits, memory and host load |

## Official references

- https://www.msys2.org/docs/environments/
- https://www.msys2.org/docs/updating/
- https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-python-pillow
- https://packages.ubuntu.com/noble/python/python3-venv
- https://docs.python.org/3/library/venv.html

