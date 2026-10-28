# Review 3 demonstration script

Good morning, Professor. Review 3 extends the sequential baseline into a native four-stage pipeline and evaluates whether overlapping different frames improves processing capacity while preserving the image transformation.

I am running the sequential C++ baseline and the pipeline on identical source frames. The same grayscale, contrast, Sobel, threshold and closing kernels are used in both. The execution architecture changes; the numerical result is held fixed.

The four pipeline workers are Fetch, Gray and contrast, Sobel with threshold and closing, and Output with buffer recycling. Three bounded queues pass buffer-slot identifiers between them. The reusable pool prevents a frame's storage from being overwritten before its output completes.

I will first show the sequential trace. Its stage rows share one thread identity. Each frame completes the four stages in order before the next frame begins.

Now I switch to the pipeline trace. The worker table shows four actual thread identities. The colored timeline bars are measured stage intervals, with color identifying a frame. Different frames overlap across workers. A single frame still follows Fetch, Gray, Edges and Output consecutively.

Using the event replay, I can move to recorded stage-start and stage-end times. The service table shows which frame was active on each worker at that time. This is playback of a completed native execution, rather than an invented animation or a live CPU-core trace. Wall-time overlap may include operating-system preemption.

For a selected captured frame, the route table shows its stage order, buffer slot and worker identity. Worker three performs the full Sobel, threshold and closing stage for that frame. We do not divide one Sobel image among all four workers.

The image panels show the actual native grayscale-after-contrast, binary Sobel and closed edge maps. The sequential and pipeline outputs must agree byte for byte for the captured frames. The black difference image makes this agreement visible. Closing changes the binary structure, while the thread scheduler preserves the result.

The capture-enabled demonstration has instrumentation and image storage costs. I therefore use the separate capture-free paired comparison for performance evaluation. It runs matching B and D treatments in randomized order and retains all measurements. Throughput is considered alongside latency and memory, and the interval describes run-level variation.

A pipeline gain is conditional, not guaranteed. More queues or threads do not automatically make the bottleneck faster. If the measured result is slower or has higher tail latency, that remains part of the evaluation.

This application validates the architecture, execution order and defined preprocessing outputs. It does not train a model, detect a plate or recognize characters. The final contribution is a controlled implementation and reproducible evaluation of the scheduling and resource tradeoffs.

