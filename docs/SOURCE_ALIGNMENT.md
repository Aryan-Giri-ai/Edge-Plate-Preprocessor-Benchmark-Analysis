# Source alignment

The project implements a preprocessing subset, rather than complete ALPR.

| Source | Connection | Project choices |
| --- | --- | --- |
| Huimin Chen, Xiaofeng Shi, Menghui Liu and Chaozheng Chen, A Chinese License Plate Recognition System based on OpenCV for complex environments, Procedia Computer Science 243 (2024), 1265–1272, Sections 4.4.1–4.4.2 | Sobel, binary threshold and morphological closing | Exact arithmetic, threshold 80, Gx-only derivative, 3×3 closing and border rules |
| Claus Neubauer and Jenn-Kwei Tyan, US6553131B1, License plate recognition with an intelligent camera, Fig. 1 block 16 | Vertical-edge extraction | Sobel is the chosen realization; the patent does not specify Sobel |
| Project systems design | Sequential and four-stage pipeline treatments | Workers, queues, reuse controls and instrumentation |

Article: https://doi.org/10.1016/j.procs.2024.09.149
Patent: https://patents.google.com/patent/US6553131B1/en

The Chen article is a conference proceedings paper in Procedia Computer Science. Neither source prescribes this exact baseline or pipeline. The fixed contrast rule and numerical constants are disclosed implementation choices.

The contribution is a controlled implementation and evaluation framework. New recognition algorithms, patentable novelty, detection or OCR accuracy are not claimed. Reference PDFs are not redistributed.

