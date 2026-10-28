# Alignment to the two PDFs supplied for Review 2

## Exact selected sources

**J1: Huimin Chen, Xiaofeng Shi, Menghui Liu and Chaozheng Chen.** *A Chinese License Plate Recognition System based on OpenCV for complex environments*. Procedia Computer Science **243 (2024), 1265–1272**. DOI: [10.1016/j.procs.2024.09.149](https://doi.org/10.1016/j.procs.2024.09.149). The attached article is a conference proceedings paper published in Procedia Computer Science. The local unchanged copy is [Chen_2024_OpenCV.pdf](../references/Chen_2024_OpenCV.pdf).

**P1: Claus Neubauer and Jenn-Kwei Tyan.** *License plate recognition with an intelligent camera*. **US6553131B1**, April 22, 2003. Local unchanged copy: [US6553131B1.pdf](../references/US6553131B1.pdf). [Public patent record](https://patents.google.com/patent/US6553131B1/en).

Both attached PDFs were inspected directly for this revision. Their hashes are in references/README.md. The Macao/Pun–Ho article selected earlier is **not** the journal attachment in this request; its histogram-equalization attribution has been removed from the default program and guides.

## Source-to-code mapping

| Source anchor | What the attachment says | Implemented connection | Boundary |
|:---|:---|:---|:---|
| J1 §4.4.1, printed p.1269, PDF page 5 | Uses Sobel edge detection | `vertical_sobel()` in shared/include/kernels.hpp uses the 3×3 Sobel Gx derivative | Gx-only is our selection to match the patent's vertical-edge step; the article passage does not freeze derivative weights, scale or border policy |
| J1 §4.4.2, printed p.1269, PDF page 5 | Sobel is followed by thresholding to a binary image and morphological closing | `vertical_sobel()` emits 0/255; `close_binary()` performs dilation then erosion | Threshold 80, full 3×3 square and zero-border policy are our explicit choices, not recovered source constants |
| P1 Fig.1 block 16, PDF page 2; coarse-localization description in printed columns 4–5 | Extracts vertical edges during coarse localization | The same absolute Gx response measures intensity changes across x, highlighting vertical boundaries | The patent does not identify this operation as Sobel and does not supply the closing implementation |
| J1 image preprocessing discussion, §3 | Discusses grayscale and other preprocessing | `gray_contrast()` supplies deterministic grayscale and the agreed contrast stage | The fixed affine contrast formula is a project choice. Histogram equalization is not used or attributed to this attachment |

The frozen common chain is:

**Fetch → Gray / fixed contrast → Vertical Sobel + binary threshold + closing → Output / recycle.**

The edge worker contains all three edge-stage operations; the architecture remains four stages and four pipeline workers. Every A–F configuration uses this same default `--profile source` and threshold.

## Sequential baseline connection

A (`edge_seq --allocation dynamic`) and B (`edge_seq --allocation pool`) execute the above operations to completion on one frame before fetching the next. A allocates three frame arrays per frame; B reuses one slot. Both have the same connection to J1 and P1. The allocation policies and sequential organization are this project's experimental controls; neither source prescribes them.

D executes the identical numerical workload with four stage workers. This permits B versus D to evaluate pipeline organization while keeping the algorithm and allocation policy fixed. A versus D includes allocation and scheduling changes together. These are controlled CPU-preprocessor baselines, not independent reimplementations of two complete recognition systems.

## Exact project choices

- RGB8 to grayscale: `Y = floor((299R + 587G + 114B + 500)/1000)`.
- Contrast: `C = clamp(floor((5Y+2)/4)-32,0,255)`. This preserves the agreed contrast-stage workload, with constants frozen for reproducibility.
- Sobel kernel: `[-1,0,1; -2,0,2; -1,0,1]`; use `abs(Gx)`.
- Binary edge pixel is 255 when the raw response is at least `--edge-threshold`, otherwise 0. Default threshold: **80** in raw 0–1020 units. A threshold of 0 deliberately retains every interior pixel, including zero gradients.
- Closing: one dilation followed by one erosion, full 3×3 square. Out-of-image values are zero for each pass; the final outer border is zero. Closing may merge nearby responses. No plate outline correctness is inferred from this operation alone.
- The input keeps its full dimensions. No automatic resize, crop, perspective correction or frame differencing is applied.
- No OpenCV calls execute inside the benchmark kernels. Explicit C++ permits consistent traversal and allocation controls. Pixel equality with unspecified OpenCV defaults is not claimed.

## Not implemented from the sources

J1's perspective correction, three-frame differencing, Gaussian normalization, HSV color mask, candidate-plate localization, character projection/segmentation, SVM and PyQt5 recognition GUI are outside the agreed preprocessor. Its HSV thresholds are not used by this workload. Its reported 96.52% recognition figure is not a result of this program and must not appear in our measured results table.

P1's subsampling, saliency map, ROI selection, tilt refinement, fine localization, segmentation and statistical classifier are outside this subset. The patent's “baseline image” means its localized plate image, not our sequential performance baseline.

The PDF's morphology wording and figure ordering are not executable specifications. This project explicitly uses the standard definition of closing (dilation then erosion), and documents all missing numerical choices instead of inventing exact original code.

## Report wording

> The sequential controls implement a defined edge-preprocessing subset informed by Chen et al. (2024), §4.4, and the vertical-edge step in US6553131B1, Fig.1 block 16. The pipeline preserves those operations. The contribution evaluated is CPU execution organization, buffer reuse, queue depth and traversal locality; no complete ALPR reproduction or recognition improvement is claimed.

## Version boundary

The initial affine-contrast plus combined `abs(Gx)+abs(Gy)` workload remains available as `--profile legacy`. It has no binary threshold or closing. The revised default uses `algorithm_id=chen-patent-edge-subset-v1`. Historical timings, including the intermediate Macao-aligned revision, must be rerun. The analyzer rejects stale algorithm identifiers, mixed profiles, mixed thresholds and captured demo runs.
