#!/usr/bin/env python3
"""Run randomized complete blocks with retained raw measurements and fingerprints."""
import argparse
import datetime
import json
import math
import os
import platform
import random
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from common import ALGORITHM_IDS, ROOT, CONFIGS, command, fingerprints, sha256, write_json

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--build", type=Path, default=ROOT / "build")
    p.add_argument("--frames", type=int, default=3000)
    p.add_argument("--repeats", type=int, default=10)
    p.add_argument("--warmup", type=int, default=120)
    p.add_argument("--rates", type=float, nargs="+", default=[0])
    p.add_argument("--configs", choices=list(CONFIGS), nargs="+", default=list(CONFIGS))
    p.add_argument("--io", choices=["file", "ram"], default="file")
    p.add_argument("--profile", choices=["source", "legacy"], default="source")
    p.add_argument("--edge-threshold", type=int, default=80)
    p.add_argument("--slots", type=int, default=34)
    p.add_argument("--seed", type=int, default=260826)
    p.add_argument("--timeout", type=float, default=3600)
    a = p.parse_args()
    if not 0 <= a.edge_threshold <= 1020:
        p.error("edge-threshold must be 0..1020")
    if a.frames < 1 or a.repeats < 1 or a.warmup < 0 or a.slots < 1 or a.timeout <= 0 or not math.isfinite(a.timeout):
        p.error("invalid frames/repeats/warmup/slots/timeout")
    if any(not math.isfinite(r) or not 0 <= r <= 1000 for r in a.rates):
        p.error("rates must be finite and in [0,1000]")
    if len(set(a.configs)) != len(a.configs) or len(set(a.rates)) != len(a.rates):
        p.error("duplicate configs/rates are not allowed; E2 is D")
    if a.out.exists():
        p.error("results directory exists; use a new --out")
    dataset_hash = sha256(a.dataset)
    manifest_path = Path(str(a.dataset)+".json")
    if not manifest_path.is_file():
        p.error("dataset .json manifest missing; run prepare_data.py")
    dataset_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if dataset_manifest.get("sha256") != dataset_hash:
        p.error("dataset hash disagrees with its manifest")
    # Validate binaries before creating a run folder.
    for c in a.configs:
        command(a.build, c, a.dataset, a.out, a.frames)
    a.out=a.out.resolve()
    if a.out.parent != (ROOT/"results").resolve():
        p.error("comparison --out must be a new direct child of this project's results/ directory")
    a.out.mkdir(parents=True)
    info = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "platform": platform.platform(), "machine": platform.machine(),
            "processor": platform.processor(), "logical_cpu_count": os.cpu_count(),
            "python": sys.version, "msystem": os.environ.get("MSYSTEM"),
            "dataset_sha256": dataset_hash, "dataset_manifest": dataset_manifest,
            "argv": sys.argv, "seed": a.seed, "frames": a.frames, "repeats": a.repeats,
            "warmup": a.warmup, "warmup_policy": "separate unpaced process before each measured run",
            "algorithm_id": ALGORITHM_IDS[a.profile], "io": a.io, "slots": a.slots, "profile": a.profile, "edge_threshold": a.edge_threshold,
            "runs": [], "complete": False}
    build_info = a.build / "build_info.txt"
    if build_info.is_file():
        info["build_info"] = build_info.read_text(encoding="utf-8")
    else:
        info["build_info"] = "Unavailable: retain CMakeCache.txt and compile_commands.json separately"
    info["source_hashes"] = {str(f.relative_to(ROOT)): sha256(f) for folder in ["src", "include", "scripts", "shared", "baseline/src", "pipeline/src"]
                             for f in sorted((ROOT/folder).rglob("*")) if f.is_file() and f.suffix in {".cpp", ".hpp", ".py", ".sh"}}
    info["binary_hashes"] = {}
    binary_paths = {}
    for c in a.configs:
        exe = Path(command(a.build,c,a.dataset,a.out,a.frames)[0])
        info["binary_hashes"][exe.name] = sha256(exe)
        binary_paths[exe.name] = exe
    write_json(a.out / "experiment.json", info)
    rng = random.Random(a.seed)
    canonical = None
    for rate in a.rates:
        for repeat in range(1, a.repeats+1):
            order = a.configs.copy()
            rng.shuffle(order)
            for position, config in enumerate(order, 1):
                name = f"r{rate:g}_block{repeat:02d}_{position}_{config}"
                if a.warmup:
                    family="baseline" if config in {"A","B"} else "pipeline"
                    warm = ROOT / family / "results" / a.out.name / "warmups" / name
                    subprocess.run(command(a.build,config,a.dataset,warm,a.warmup,0,a.io,a.slots,profile=a.profile,edge_threshold=a.edge_threshold),
                                   check=True, timeout=a.timeout, stdout=subprocess.DEVNULL)
                family="baseline" if config in {"A","B"} else "pipeline"
                dest = ROOT / family / "results" / a.out.name / "runs" / name
                cmd = command(a.build,config,a.dataset,dest,a.frames,rate,a.io,a.slots,profile=a.profile,edge_threshold=a.edge_threshold)
                print(f"[{rate:g} FPS input | block {repeat}/{a.repeats} | {config}]", flush=True)
                done = subprocess.run(cmd, check=True, timeout=a.timeout, capture_output=True, text=True)
                print(done.stdout.strip(), flush=True)
                fp = fingerprints(dest)
                if len(fp) != a.frames:
                    raise RuntimeError("incorrect number of output fingerprints")
                if canonical is None:
                    canonical = fp
                elif fp != canonical:
                    raise RuntimeError(f"Output fingerprint mismatch: {name}. Do not analyze this experiment.")
                summary = json.loads((dest/"summary.json").read_text())
                if summary.get("algorithm_id") != ALGORITHM_IDS[a.profile]:
                    raise RuntimeError("Wrong/stale executable algorithm; rebuild both programs")
                if summary["elapsed_s"] < 5:
                    print("NOTE: run shorter than 5 s; suitable for a pilot, increase --frames for final measurements.", flush=True)
                entry = {"name": name, "config": config, "rate": rate, "block": repeat,
                         "position": position, "path": Path(os.path.relpath(dest,a.out)).as_posix(), "command": cmd,
                         "fingerprints_match": True}
                info["runs"].append(entry)
                write_json(a.out/"experiment.json",info)
    # Detect input or executable changes during a long experiment.
    if sha256(a.dataset) != dataset_hash:
        raise RuntimeError("Dataset changed during experiment")
    for name, expected in info["binary_hashes"].items():
        if sha256(binary_paths[name]) != expected:
            raise RuntimeError("Binary changed during experiment")
    info["complete"] = True
    write_json(a.out/"experiment.json",info)
    subprocess.run([sys.executable,str(ROOT/"scripts"/"analyze.py"),str(a.out)], check=True)
    print(f"Finished. Read {a.out/'analysis.md'}")

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as e:
        print(f"ERROR: {e}",file=sys.stderr)
        sys.exit(1)
