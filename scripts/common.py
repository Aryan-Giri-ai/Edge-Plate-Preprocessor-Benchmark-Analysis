import csv
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALGORITHM_IDS = {"source": "chen-patent-edge-subset-v1", "legacy": "affine-l1-v1"}
CONFIGS = {
    "A": ("edge_seq", "dynamic", "row", 5),
    "B": ("edge_seq", "pool", "row", 5),
    "C": ("edge_pipeline", "dynamic", "row", 5),
    "D": ("edge_pipeline", "pool", "row", 5),
    "E1": ("edge_pipeline", "pool", "row", 2),
    "E3": ("edge_pipeline", "pool", "row", 10),
    "F": ("edge_pipeline", "pool", "column", 5),
}

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def executable(build, name):
    folder=Path(build).resolve()
    if folder == (ROOT/"build").resolve() and name in {"edge_seq","edge_pipeline"}:
        folder=ROOT/("baseline" if name=="edge_seq" else "pipeline")/"build"
    p = folder / (name + (".exe" if os.name == "nt" else ""))
    if not p.is_file():
        raise FileNotFoundError(f"Missing {p}; run bash scripts/build.sh first")
    return str(p)

def command(build, config, dataset, out, frames, rate=0, io="file", slots=34, capture=0, profile="source", edge_threshold=80):
    name, allocation, traversal, queue = CONFIGS[config]
    return [executable(build, name), "--input", str(Path(dataset).resolve()),
            "--out", str(Path(out).resolve()), "--frames", str(frames),
            "--allocation", allocation, "--traversal", traversal,
            "--queue", str(queue), "--slots", str(slots), "--rate", str(rate),
            "--io", io, "--capture", str(capture),
            "--profile", profile, "--edge-threshold", str(edge_threshold)]

def fingerprints(run):
    if not (Path(run) / "SUCCESS").is_file():
        raise RuntimeError(f"Incomplete run: {run}")
    with (Path(run) / "frames.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    for i, row in enumerate(rows):
        if int(row["frame_id"]) != i:
            raise RuntimeError(f"Missing, duplicated or reordered frame in {run}")
    return [(r["source_index"], r["sum"], r["weighted_sum"]) for r in rows]

def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
