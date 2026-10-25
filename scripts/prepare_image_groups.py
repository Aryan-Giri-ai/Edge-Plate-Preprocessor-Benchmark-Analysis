#!/usr/bin/env python3
"""Prepare authorized images at their original sizes, one RGB replay per resolution."""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from PIL import Image, __version__ as pillow_version
from common import sha256, write_json
from prepare_data import write_raw

def prepare(input_root, output_root, limit=0):
    input_root, output_root = Path(input_root).resolve(), Path(output_root).resolve()
    if not input_root.is_dir() or limit < 0:
        raise ValueError("input must be a directory and limit must be nonnegative")
    if output_root.exists():
        raise ValueError("output exists; choose a fresh directory")
    if output_root.is_relative_to(input_root):
        raise ValueError("output must be outside the input tree")
    paths = sorted((p for p in input_root.rglob("*") if p.is_file() and
                    p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".ppm"}),
                   key=lambda p: p.relative_to(input_root).as_posix())
    available = len(paths)
    if not paths:
        raise ValueError("no supported images found")
    if limit and limit < available:
        paths = ([paths[0]] if limit == 1 else
                 [paths[i * (available - 1) // (limit - 1)] for i in range(limit)])
    groups = defaultdict(list)
    for p in paths:
        with Image.open(p) as img:
            width, height = img.size
            if not (3 <= width <= 8192 and 3 <= height <= 8192):
                raise ValueError(f"unsupported original dimensions {img.size}: {p}")
            img.verify()
        groups[(width, height)].append(p)
    expected_bytes = sum(20 + 3*w*h*len(items) for (w,h),items in groups.items())
    print(f"Selected {len(paths)} of {available} supported images; {len(groups)} resolution groups.", flush=True)
    print(f"Decoded replay estimate: {expected_bytes} bytes; no resizing or cropping.", flush=True)
    output_root.mkdir(parents=True)
    index = {"complete": False, "available_images": available, "selected_images": len(paths),
             "selection": "uniform over sorted relative paths before grouping",
             "limit": limit, "expected_replay_bytes": expected_bytes, "groups": []}
    write_json(output_root/"groups.json", index)
    for (w,h), items in sorted(groups.items()):
        replay = output_root/f"{w}x{h}.epraw"
        sources = []
        def frames():
            for p in items:
                before = sha256(p)
                with Image.open(p) as img:
                    if img.size != (w,h):
                        raise ValueError(f"source dimensions changed: {p}")
                    rgb = img.convert("RGB").tobytes()
                if sha256(p) != before:
                    raise ValueError(f"source changed during preparation: {p}")
                sources.append({"index": len(sources), "path": p.relative_to(input_root).as_posix(),
                                "source_sha256": before})
                yield rgb
        write_raw(replay,w,h,len(items),frames())
        manifest = {"format": "EPRAW01", "kind": "images", "width": w, "height": h,
                    "count": len(items), "available_images": available, "selected": sources,
                    "selection": index["selection"], "pillow": pillow_version,
                    "conversion": "Pillow RGB, original dimensions, no resize/crop/EXIF transpose",
                    "file_bytes": replay.stat().st_size, "sha256": sha256(replay)}
        write_json(str(replay)+".json",manifest)
        index["groups"].append({"replay": replay.name, "width": w, "height": h, "count": len(items),
                                "sha256": manifest["sha256"]})
        write_json(output_root/"groups.json",index)
        print(f"Created {replay.name}: {len(items)} distinct images", flush=True)
    index["complete"] = True
    write_json(output_root/"groups.json",index)
    return index

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--limit",type=int,default=0,help="0=all supported images; otherwise uniform subset")
    a=p.parse_args()
    try:
        prepare(a.input,a.out,a.limit)
    except (OSError,ValueError) as error:
        p.exit(1,f"ERROR: {error}\n")
if __name__=="__main__":
    main()

