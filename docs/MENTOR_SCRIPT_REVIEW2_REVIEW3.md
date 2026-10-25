# Combined Review 2 and Review 3 mentor script

Approximate speaking time: 6–8 minutes excluding program execution. Bracketed directions are cues, not spoken lines. Replace the local-result placeholders only after your own successful benchmark. The historical figures below are verified saved Linux results.

## Opening and problem

Good morning, Professor. My project evaluates whether a four-stage software pipeline can increase the processing throughput of a license-plate image preprocessing workload while preserving the same output as a sequential program.

The work is divided into two progress stages. Review 2 establishes the reference algorithm, architecture, gaps and evaluation design. Review 3 demonstrates the implementation, thread behavior and measured performance tradeoffs.

The practical issue is that sequential execution finishes every stage of one frame before starting the next. My proposed architecture overlaps different processing stages across successive frames. The question is whether this overlap provides a useful throughput gain after synchronization, waiting and memory costs are included.

## Review 2: baseline, source alignment and contribution

[Show baseline/, pipeline/ and shared/.]

I created separate sequential and pipeline programs under a common project root. Both call the same numerical kernels, so their comparison changes execution organization while preserving the computation.

The preprocessing sequence is frame fetching, grayscale conversion and fixed contrast adjustment, vertical Sobel filtering, binary thresholding, morphological closing, and output handling. These operations are organized into four stages because Sobel, thresholding and closing belong to the same edge-processing stage.

The selected Chen and co-authors paper supports Sobel, thresholding and closing. US6553131B1 supports the vertical-edge extraction rationale. The project implements that preprocessing subset. The threshold, contrast arithmetic, closing window and border behavior are explicitly documented project choices.

The gap addressed here is a controlled architectural comparison for this workload. My contributions are the matched implementations, bounded buffer ownership, reproducible preparation and benchmarking, and an auditable thread-and-image demonstration. I am not presenting Sobel or software pipelining as newly invented algorithms.

For architecture justification, I established seven configurations. A and B compare sequential dynamic allocation with reuse. C and D compare the same choice in the pipeline. B versus D is the primary scheduling comparison with reuse in both. Queue capacities two, five and ten test queue behavior, and row versus column traversal tests memory-access organization.

## Review 3: how the threads work

[Show console.txt and the D timeline.]

The pipeline uses four persistent workers. Worker one fetches a frame into an owned buffer slot. Worker two performs grayscale conversion and contrast adjustment. Worker three performs vertical Sobel, thresholding and closing. Worker four copies and fingerprints the output, then returns the slot for reuse.

Three bounded queues transfer slot identifiers between stages. A worker waits when its input is empty or its output queue is full. The buffer remains owned until processing completes, which prevents it from being overwritten while another stage uses it.

The timeline shows actual measured worker identities and frame-stage intervals. Different frames overlap across the four workers. This is stage parallelism; the program does not divide one image's Sobel calculation across four threads. Thread identities also do not identify physical CPU cores.

## Visual demonstration and correctness

[Show input, grayscale, binary Sobel, closed edges, closing-change and B–D difference.]

The grayscale map is the input to the edge stage. Sobel emphasizes vertical boundaries; thresholding produces the binary map. Morphological closing performs dilation followed by erosion and can connect nearby binary structures.

The changed-pixel image shows what closing altered. It is a description of the transformation, not an accuracy score. The baseline–pipeline difference is black for the captured frames because both implementations produce identical pixels.

I also use an independent small-image reference, full-byte capture comparisons and run-level audits. The audits check frame order, worker identity, slot reuse, queue bounds and output fingerprints. This prevents interpreting a faster run that accidentally skips work or changes the output.

## Benchmark methodology

[Show the fresh SUMMARY.txt and audit result, or clearly identify the historical example.]

The capture-enabled demo is separate from the performance experiment. During benchmarking, image capture is disabled. Both programs receive the same replay, source profile, threshold and numerical operators.

The planned primary experiment uses ten randomized paired blocks. It records throughput, admitted-frame P95 and P99 latency, CPU use, peak process memory, stage intervals and queue waits. Speedup is calculated from paired run ratios, and its interval is based on run-level bootstrap resampling.

The processing timer excludes PNG decoding, setup and report display. It includes processing, frame reads or copies, output fingerprints, queue synchronization and pipeline fill and drain. These boundaries make the result a preprocessing comparison rather than complete camera-to-recognition latency.

## Results and tradeoffs

For the verified saved Linux sample, six distinct UFPR-ALPR testing images were replayed for 600 frames per run across twenty timed B/D processes. The paired throughput ratio was 1.520, with a 95 percent interval from 1.498 to 1.545.

The pipeline improved processing capacity in that experiment, but P95 latency increased from about 19.3 to 178.6 milliseconds, and peak memory increased from about 19.6 to 339.8 MiB. That means a higher completed-frame rate did not imply a shorter wait for each admitted frame.

[If presenting a successful new local run, continue: On this system, my new paired ratio is INSERT RATIO. The P95 values are INSERT B AND D VALUES, and peak memory is INSERT B AND D VALUES. These numbers come from the summary displayed here.]

Older ablations did not support a pooling throughput benefit on that setup, and larger queues showed no resolved throughput advantage. Those results remain in the evaluation. A larger queue can store more waiting frames without making the bottleneck faster.

## Limitations and next steps

The saved performance result is limited to six distinct images and its Linux host. Replaying them does not create new visual diversity. The public project is portable across its documented environments, but each new host needs its own measurements.

This implementation does not train a model, locate a plate or recognize characters. Detection accuracy and OCR accuracy are therefore not evaluation outputs. Cache misses, IPC and energy were not measured either.

My next validation is to run the same protocol on the intended evaluation machine and a broader authorized image selection, preserving original resolutions. The objective is to establish where the throughput benefit remains useful and whether latency and memory costs meet the application requirements.

