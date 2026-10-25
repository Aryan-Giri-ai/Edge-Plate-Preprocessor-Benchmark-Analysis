# Review 2 demo

Follow sections 1–9 of [MSYS_UFPR_GUIDE.md](MSYS_UFPR_GUIDE.md). The packaged offline demo is [results/thread_demo/index.html](../results/thread_demo/index.html). It uses actual 60-frame A/B/D runs over six selected training images and includes two captured frames. Captured edge bytes and every frame fingerprint agree across A/B/D. Baseline and pipeline full grayscale/edge equality for all 18 initialization images is recorded separately in results/drive_init.

Open the offline page after extracting the complete ZIP. Choose A, B or D, change the first frame in the timeline, and move the captured-image slider. Read stage/worker and queue tables below it. Wall-time overlap is not a CPU-core trace. Recreate a longer demo from your own installed data using scripts/demo.py. Use the repeated study, with capture disabled, for performance conclusions.
