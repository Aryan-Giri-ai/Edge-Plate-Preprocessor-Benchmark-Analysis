# Sequential baseline project

Build from the head folder with `bash baseline/build.sh`. The native executable is `baseline/build/edge_seq.exe` on MSYS2 UCRT64.

Run `python baseline/run.py --prepared data/prepared/ufpr_init --split training --run-name baseline_trial --config B --capture 4` from the head folder. Configuration A allocates three arrays per frame; B reuses one slot. Results are written only under `baseline/results/` for this launcher.

The explicit C++ entry point is `src/main.cpp`. Numerical kernels and measurement implementation are shared in `../shared/`. Use the same source profile and input replay as the pipeline. There is no trained estimator or weights file.
