# Four-stage pipeline

Build from the root with bash pipeline/build.sh. Linux executable: pipeline/build/edge_pipeline; MSYS2 UCRT64 adds .exe.

Four persistent workers overlap different frames: Fetch, Gray/contrast, Sobel/threshold/closing and Output/recycle. Bounded queues pass slot IDs. D uses queue capacity 5 and 34 pooled slots. C, E1, E3 and F provide allocation, queue and traversal controls.

Use scripts/review3_demo.py for visual output and worker records, or scripts/run_review3.py for paired benchmarks. Native records are under pipeline/results/. Threads are not pinned to CPU cores.


Single-family demonstration from the root:

~~~bash
python pipeline/run.py --dataset data/prepared/synthetic_01.epraw --run-name separate_01 --frames 120 --capture 3
~~~

Use a fresh run-name each time. The launcher saves raw captures and records; use the joint demo for its HTML viewer.
