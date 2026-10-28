# Source and implementation alignment

The engine/shared files and engine/baseline/src/main.cpp are unchanged copies from the GitHub-ready project's sequential source. Native mode invokes that implementation with pooled allocation and captures enabled.

The Python implementation follows the same RGB integer luminance, fixed affine contrast, absolute Gx, threshold, 3×3 closing and zero-border rules. It is a separately implemented sequential equivalent, validated on the cases in tests/check_app.py. Numerical agreement does not make Python and C++ timing comparable.

Chen, Shi, Liu and Chen, A Chinese License Plate Recognition System based on OpenCV for complex environments, Procedia Computer Science 243 (2024), 1265–1272, Sections 4.4.1–4.4.2, supports Sobel/threshold/closing. This is a proceedings article. DOI: https://doi.org/10.1016/j.procs.2024.09.149

Claus Neubauer and Jenn-Kwei Tyan, US6553131B1, License plate recognition with an intelligent camera, Fig. 1 block 16, motivates vertical edges. The patent does not specify Sobel. https://patents.google.com/patent/US6553131B1/en

Gx-only selection, threshold 80, contrast arithmetic and borders are explicit project choices. The application implements preprocessing, not the full recognition system.

UFPR data is obtained separately under its owners' terms. No traffic images, annotations or reference PDFs are included. Streamlit, NumPy and Pillow are installed separately and retain their own licenses.

