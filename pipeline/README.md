# Pipelined preprocessor project

Build from the head folder with `bash pipeline/build.sh`. The native executable is `pipeline/build/edge_pipeline.exe` on MSYS2 UCRT64.

Run `python pipeline/run.py --prepared data/prepared/ufpr_init --split training --run-name pipeline_trial --config D --capture 4` from the head folder. D uses four stage workers, reused buffers, queue depth 5 and 34 slots. C, E1, E3 and F provide the agreed controls. Results are written under `pipeline/results/` for this launcher.

The explicit C++ entry point is `src/main.cpp`. Shared functions in `../shared/` keep pixel operations identical to the sequential program. Parallelism is across frames in different stages. There is no model fitting.
