# Dataset connection and storage

`drive_inventory.json` records the 150 track folders and all 4,500 image/annotation pairs observed in the user's Drive on 2026-10-02. It is metadata, not the image dataset. The original folder is https://drive.google.com/drive/folders/1qDhsc30Td6qPn6gKIC9vv6vtrDGvFBzi .

Use `scripts/prepare_ufpr.py` or `scripts/initialize.py` with the actual local dataset root. Keep training, validation and testing separate. Prepared EPRAW files are shared between programs; each has a manifest with image/annotation hashes, split, camera and annotation-derived geometry. The C++ kernels see decoded pixels only.

The archive includes the manifests from the 18-image initialization sample but excludes their large EPRAW payloads. Regenerate a new preparation from your own installed data before running. To avoid confusing sample evidence with a reusable full dataset, use a new run name such as `ufpr_init` and do not point launchers at the included sample manifests alone.

Cite the dataset source in your report: Laroca et al., “A Robust Real-Time Automatic License Plate Recognition Based on the YOLO Detector,” IJCNN, 2018, pp.1–10. This project's Sobel pipeline does not reproduce that YOLO system or borrow its recognition results.
