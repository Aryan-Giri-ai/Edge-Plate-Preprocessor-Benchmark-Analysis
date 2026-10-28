# Review 2 sequential preprocessing application

This is a local Streamlit application for demonstrating the baseline image transform in sequence. The interface supports generated patterns, uploaded images and a selected image from an installed local dataset.

It displays original RGB, integer grayscale, fixed contrast, absolute vertical Sobel response, thresholded edges, final morphological closing and changed pixels. Processing runs only when Run sequential preprocessing is submitted. Images and a JSON run record can be downloaded.

## 1 Exact new project location

Keep the previous Review 2 and GitHub-ready project folders intact. Save Review2_Sequential_Streamlit.zip into E:\myCAO catalog and use this separate folder:

E:\myCAO catalog\Review2App01\Review2_Sequential_Streamlit

The confirmed dataset search location is:

E:\NEW DOWNLOADS\VIT Downloads\Other Downloads\Assignments

The app scans supported image files beneath the folder you select. For a focused real-image demonstration, point to the actual UFPR testing subfolder once located. No dataset images are included or downloaded automatically.

## 2 Install standard Windows Python and VS Code

Use ordinary Windows CPython 3.12 for the Streamlit environment. It is separate from the Python installed under E:\msys64\main file. Install Python from https://www.python.org/downloads/windows/ and VS Code from https://code.visualstudio.com/.

Install Microsoft's Python and Python Debugger extensions in VS Code. Python 3.12 is a selected compatible version, not a hardware requirement.

Open a PowerShell terminal (not MSYS2 for this application environment). Check:

~~~powershell
py -0p
py -3.12 --version
~~~

If 3.12 is unavailable, install it before continuing. Avoid changing the MSYS2 installation to install Streamlit.

## 3 Extract and create the application environment

Run once in PowerShell. The destination must be new.

~~~powershell
Set-Location "E:\myCAO catalog"
Expand-Archive -LiteralPath ".\Review2_Sequential_Streamlit.zip" -DestinationPath ".\Review2App01"
Set-Location ".\Review2App01\Review2_Sequential_Streamlit"
py -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -c "import streamlit, numpy, PIL; print('Application dependencies ready')"
~~~

Using the environment's executable directly avoids PowerShell script-activation policy problems. If E:\myCAO catalog\Review2App01 already exists, use a fresh extraction destination rather than combining versions.

## 4 Open the correct VS Code folder

In VS Code choose File → Open Folder and select:

E:\myCAO catalog\Review2App01\Review2_Sequential_Streamlit

Press Ctrl+Shift+P → Python: Select Interpreter → Enter interpreter path. Select:

E:\myCAO catalog\Review2App01\Review2_Sequential_Streamlit\.venv\Scripts\python.exe

Open Terminal → New Terminal and choose PowerShell. Confirm app.py and processing.py are in the selected folder.

~~~powershell
Get-Location
Get-ChildItem app.py, processing.py
& ".\.venv\Scripts\python.exe" -c "import sys; print(sys.executable)"
~~~

## 5 Launch the interface

Run in the VS Code PowerShell terminal:

~~~powershell
& ".\.venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1
~~~

Open http://127.0.0.1:8501 in the browser. Streamlit prints the actual URL if the port differs. Stop with Ctrl+C in the terminal. Do not run app.py with the ordinary Run Python File button; it must be started through Streamlit.

The supplied .vscode/launch.json also supports F5 after selecting the virtual-environment interpreter. The terminal command is the clearest first-run path.

## 6 First demonstration without a native build

Choose Generated pattern, choose Python sequential, keep threshold 80, and press Run sequential preprocessing. The generated pattern is explicitly synthetic.

The Python implementation uses the same integer grayscale, contrast, Gx, threshold and border rules as the native project. It executes operations one after another and creates no stage-worker pipeline. NumPy's internal implementation is not a CPU-core execution trace.

Choose Upload image to process your own PNG/JPEG/BMP/PPM. For your installed dataset:

1. Choose Local dataset.
2. Leave the confirmed Assignments path or enter the exact UFPR/testing subfolder.
3. Press Find images.
4. Select the required image.
5. Choose the engine and threshold.
6. Press Run sequential preprocessing.

Scanning only locates files. It does not process all images or train a model. Images are converted to RGB at their original size; no resize, crop or EXIF rotation is silently applied. The app supports images up to 12 megapixels with sides from 3 to 8192 pixels.

Results stay labeled with the source, threshold and engine that produced them. Changing controls does not change the prior completed output until you submit again.

## 7 Enable the actual C++ baseline for the mentor demonstration

The Python route works without a compiler. For a demonstration of the original native baseline, build the included C++ source once. The engine/shared and engine/baseline files are unchanged copies of the GitHub-ready sequential implementation.

Open MSYS2 UCRT64:

~~~bash
cd "/e/myCAO catalog/Review2App01/Review2_Sequential_Streamlit"
bash native/build.sh
ls native/bin/edge_seq.exe
~~~

Once built, return to the VS Code PowerShell terminal. Stop Streamlit with Ctrl+C if it is running. Add the UCRT64 runtime location shown in your earlier traceback:

~~~powershell
$env:PATH = "E:\msys64\main file\ucrt64\bin;" + $env:PATH
& ".\.venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1
~~~

The explicit .venv executable continues to select standard Windows Python even though the compiler runtime directory is on PATH. Repeat the PATH command in each new terminal when using the native engine. If MSYS2 was installed elsewhere, use its actual ucrt64\bin directory.

Choose Native C++ sequential and Run. The application sends a one-frame RGB replay to edge_seq with pooled allocation, row traversal, the source profile, the selected threshold and capture enabled.

The three captured planes—contrast grayscale, binary Sobel and final closed edges—are compared byte for byte with the Python equivalent. A mismatch rejects the result. The app displays the actual native frame/worker records and processing interval. Raw grayscale before contrast and Sobel-strength previews are Python diagnostics rather than extra native capture planes.

This is the sequential C++ baseline, not the four-worker pipeline. Temporary native replay files are removed after the result is loaded.

## 8 What to demonstrate and say

| Display | Concept |
| --- | --- |
| Original RGB | Actual input; state whether it is UFPR, an upload or synthetic |
| Grayscale | Weighted integer luminance |
| Fixed contrast | The documented affine adjustment before edges |
| Sobel response | Absolute horizontal derivative Gx emphasizing vertical boundaries |
| Thresholded map | Strong responses become 255; weaker responses become zero |
| Closed edges | Dilation then erosion using a full 3×3 square |
| Closing change | Pixels changed by morphology, not an accuracy score |
| Stage record | Operations occur sequentially for the selected frame |
| Native records | Actual native execution identity and byte agreement |
| Download | Actual output maps and reproducible run settings |

The Sobel preview uses a fixed response scale of 0–1020 mapped to 0–255 for display. The threshold uses the unscaled response. Threshold 80 reproduces the default; other thresholds are exploratory choices, not optimized settings.

The UI shows seven visual panels, while the original project has four architecture stages: Fetch; Gray/contrast; Sobel/threshold/closing; Output. Splitting a stage into explanatory panels does not add native worker stages.

The selected Chen et al. paper supports Sobel, thresholding and closing. US6553131B1 supports the vertical-edge rationale and does not specify Sobel. Exact arithmetic and constants are project choices. See SOURCE_ALIGNMENT.md.

Single-image GUI timings are demonstration measurements. They do not replace the capture-free repeated B/D benchmarks in the existing project and cannot establish a speedup against the pipeline.

## 9 Tests and Linux setup

Full verification requires the native engine:

~~~powershell
$env:PATH = "E:\msys64\main file\ucrt64\bin;" + $env:PATH
& ".\.venv\Scripts\python.exe" tests/check_app.py
~~~

On Linux, use standard Python 3.12 and a C++20 compiler:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
bash native/build.sh
python tests/check_app.py
python -m streamlit run app.py --server.address 127.0.0.1
~~~

Validation completed here on Linux includes an independent scalar reference, threshold boundaries, small/border cases, 1920×1080 native capture parity, output export and Streamlit form/engine/error behavior. Windows execution still needs the checks on your machine. No UFPR source images were used for these new app checks.

## 10 Troubleshooting

| Problem | Action |
| --- | --- |
| py -3.12 not found | Install ordinary Windows CPython 3.12 and reopen VS Code |
| No module named streamlit | Install requirements with the exact .venv executable |
| PowerShell activation blocked | Use .venv\Scripts\python.exe directly as above |
| Browser fails to open | Enter the local URL printed by Streamlit |
| Port 8501 occupied | Add --server.port 8502 and open that printed URL |
| Native executable missing | Build with native/build.sh in UCRT64, or select Python sequential |
| Native exit code with no text / missing DLL | Add the correct UCRT64 bin directory to the launch terminal PATH |
| No dataset images found | Point at the extracted image directory; a ZIP or Drive web URL is not a directory |
| Results did not change | Submit Run after changing the controls; prior results remain labeled |
| Changed pixels seem better/worse | Inspect the image; white-pixel count is not detection or OCR accuracy |

## 11 Repository and hosting

This application can be added as a separate review2_app directory in your source repository, or kept as this standalone project. Keep .venv, compiled native binaries, local datasets and generated captures out of Git. The included MIT license applies to original project code; dataset and dependency licenses are separate.

The recommended review is hosted locally on your laptop. A remote Streamlit server cannot access the E: drive on your PC. For remote hosting, use image uploads or authorized server-local data. The Python engine can run without a native compiler; the native engine needs a server-built Linux executable. No external deployment has been performed.

## References

- Streamlit installation: https://docs.streamlit.io/get-started/installation/command-line
- VS Code Python environments: https://code.visualstudio.com/docs/python/environments
- Dataset ownership and access: https://github.com/raysonlaroca/ufpr-alpr-dataset
- Base article: https://doi.org/10.1016/j.procs.2024.09.149
- Patent: https://patents.google.com/patent/US6553131B1/en

