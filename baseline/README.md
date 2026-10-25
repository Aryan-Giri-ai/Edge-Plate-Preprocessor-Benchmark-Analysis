# Sequential baseline

Build from the root with bash baseline/build.sh. Linux executable: baseline/build/edge_seq; MSYS2 UCRT64 adds .exe.

A allocates frame arrays dynamically. B reuses one slot and is the primary reference. Both finish Fetch, Gray/contrast, Sobel/threshold/closing and Output for one frame before starting the next.

Use scripts/review3_demo.py for A/B/D visual comparison and scripts/run_review3.py for joint B/D benchmarking. Shared kernels live in shared/. Native records are under baseline/results/.


Single-family demonstration from the root:

~~~bash
python baseline/run.py --dataset data/prepared/synthetic_01.epraw --run-name separate_01 --frames 120 --capture 3
~~~

Use a fresh run-name each time. The launcher saves raw captures and records; use the joint demo for its HTML viewer.
