# Review 2 speaking script

Approximate duration: four to five minutes, with short pauses to operate the interface. Use native mode when claiming to demonstrate the original C++ baseline. Identify Python mode as the sequential equivalent.

Good morning, Professor. For Review 2, I am demonstrating the sequential image preprocessing baseline through an application interface. The objective at this stage is to make the algorithm and its execution order visible before comparing it with the proposed pipeline.

This application accepts an uploaded image or a selected image from my installed dataset. I can also use a generated pattern to check the application, but I identify that input as synthetic. I will use a real traffic image for the project demonstration.

The processing begins only when I press Run sequential preprocessing. The source, threshold and engine are recorded with the output, so a displayed image can be traced to its settings.

The first operation converts RGB into grayscale using weighted integer luminance. This reduces three color channels to one intensity value. The next operation applies the fixed contrast adjustment specified in the project.

The Sobel stage uses the Gx derivative. Although it measures intensity changes across the horizontal direction, it emphasizes vertical boundaries in the image. Vertical strokes can be relevant to license-plate characters, but background objects can also produce strong edges.

The response image shows the strength of those changes. For display it uses a fixed scale, while thresholding uses the original numerical response. With the baseline threshold of eighty, responses meeting the threshold become white and the remaining pixels become black.

The next operation is morphological closing: dilation followed by erosion with a three-by-three square. It can connect nearby binary structures and close small gaps. The changed-pixel panel shows what this operation altered. I do not treat the number of white pixels as an accuracy measurement.

The program performs these operations sequentially. It completes the stages for one selected frame before another frame is processed. The interface displays more individual image panels for explanation, but the underlying architecture is still described by four stages: fetching, grayscale and contrast, edge processing, and output handling.

In native mode, the interface runs the original pooled C++ sequential baseline. It captures the actual grayscale-after-contrast, binary Sobel and final edge buffers. These outputs are checked against the Python equivalent before the result is accepted. The native worker record identifies the execution thread; it is not a CPU core number.

If using Python mode instead, I identify it as a sequential implementation with the same numerical rules. I do not present its timings as measurements of the C++ executable.

The selected Chen and co-authors paper supports Sobel, binary thresholding and morphological closing. The selected US patent supports the vertical-edge extraction rationale. The exact contrast arithmetic, threshold, window and border policy are disclosed project choices rather than a complete reproduction of either recognition system.

The proposed contribution is architectural and experimental. In the next implementation stage, different frames can overlap across four persistent workers connected through bounded queues. Both versions must preserve the same preprocessing output so that a throughput difference can be attributed to the execution design rather than a different image algorithm.

For that comparison, I will use the separate repeated benchmark workflow. The interface timing is useful for demonstration, but it includes a different execution context and is not the primary performance experiment. The project evaluation considers throughput, latency, CPU use, peak memory, allocation behavior and queue effects together.

The current limitation is that an edge map is an intermediate representation. This application does not train a model, locate a plate or recognize characters. Review 2 establishes the baseline, source alignment and evaluation plan. Review 3 examines whether the pipeline increases processing capacity and what latency and memory costs accompany it.

