#!/usr/bin/env python3
"""Build a reproducible RGB replay file. No model training or network download."""
import argparse
import json
import platform
import random
import struct
import sys
from pathlib import Path
from common import sha256, write_json

MAGIC = b"EPRAW01\n"

def write_raw(path, width, height, count, frames):
    if not (3 <= width <= 8192 and 3 <= height <= 8192 and 1 <= count <= 1000000):
        raise ValueError("width/height 3..8192, frame count 1..1000000 required")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidentally overwriting a previous dataset.
    with path.open("xb") as f:
        f.write(MAGIC + struct.pack("<III", width, height, count))
        actual = 0
        for rgb in frames:
            if len(rgb) != width * height * 3:
                raise ValueError("incorrect RGB frame length")
            f.write(rgb)
            actual += 1
        if actual != count:
            raise ValueError(f"expected {count} frames; got {actual}")

def synthetic_frames(w, h, count, seed):
    rng = random.Random(seed)
    for i in range(count):
        if i % 3 == 0:
            yield rng.randbytes(w * h * 3)
        elif i % 3 == 1:
            row = b"".join(bytes(((x+i) % 256, (2*x+i) % 256, (3*x+i) % 256)) for x in range(w))
            yield row * h
        else:
            row = b"".join(bytes((235, 235, 235) if ((x+i)//9) % 2 else (20, 20, 20)) for x in range(w))
            yield row * h

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="kind", required=True)
    syn = sub.add_parser("synthetic")
    syn.add_argument("--width", type=int, default=1920)
    syn.add_argument("--height", type=int, default=1080)
    syn.add_argument("--count", type=int, default=16)
    syn.add_argument("--seed", type=int, default=260826)
    real = sub.add_parser("images")
    real.add_argument("--input", type=Path, required=True)
    real.add_argument("--limit", type=int, default=0, help="0=all images")
    real.add_argument("--selection", choices=["uniform", "first"], default="uniform")
    for child in (syn, real):
        child.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists() or Path(str(a.out)+".json").exists():
        p.error("output or its manifest already exists; choose a new name")
    manifest = {"format": "EPRAW01", "kind": a.kind, "python": platform.python_version()}
    if a.kind == "synthetic":
        write_raw(a.out, a.width, a.height, a.count, synthetic_frames(a.width, a.height, a.count, a.seed))
        manifest.update(width=a.width, height=a.height, count=a.count, seed=a.seed,
                        description="Generated noise, RGB ramps and stripes; NOT traffic-camera data")
    else:
        from PIL import Image, __version__ as pillow_version
        root = a.input.resolve()
        if not root.is_dir() or a.limit < 0:
            p.error("input must be an existing directory and limit must be nonnegative")
        paths = sorted((f for f in root.rglob("*") if f.is_file() and f.suffix.lower() in
                        {".png", ".jpg", ".jpeg", ".bmp", ".ppm"}), key=lambda f: f.relative_to(root).as_posix())
        available = len(paths)
        if not paths:
            p.error("no supported images found")
        if a.limit and a.limit < len(paths):
            if a.selection == "first" or a.limit == 1:
                paths = paths[:a.limit]
            else:
                paths = [paths[(i*(available-1))//(a.limit-1)] for i in range(a.limit)]
        with Image.open(paths[0]) as img:
            w, h = img.size
        selected = []
        def frames():
            for i, file in enumerate(paths):
                with Image.open(file) as img:
                    if img.size != (w, h):
                        raise ValueError(f"Dimension mismatch: {file}; no implicit resizing is allowed")
                    rgb = img.convert("RGB").tobytes()
                selected.append({"index": i, "path": file.relative_to(root).as_posix(),
                                 "source_sha256": sha256(file)})
                yield rgb
        write_raw(a.out, w, h, len(paths), frames())
        manifest.update(width=w, height=h, count=len(paths), available_images=available,
                        selection=a.selection, pillow=pillow_version, selected=selected,
                        conversion="Pillow convert RGB, original pixel dimensions, no crop, no resize, no EXIF transpose")
    manifest.update(file_bytes=a.out.stat().st_size, sha256=sha256(a.out))
    write_json(str(a.out)+".json", manifest)
    print(f"Created {a.out}: {manifest['count']} frames, {manifest['width']}x{manifest['height']}, {manifest['file_bytes']} bytes")
    print("Keep the adjacent .json manifest with the replay file.")

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, ImportError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
