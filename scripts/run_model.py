#!/usr/bin/env python3
"""Launch one implementation on a prepared RGB replay; no model training."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from common import ROOT, command, sha256, write_json

def main(family):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset",type=Path,required=True)
    p.add_argument("--run-name",required=True)
    p.add_argument("--frames",type=int,default=120)
    p.add_argument("--capture",type=int,default=3)
    p.add_argument("--config",choices=["A","B"] if family=="baseline" else ["C","D","E1","E3","F"])
    a=p.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+",a.run_name):
        p.error("run-name must use letters, numbers, underscore or hyphen")
    if a.frames<1 or not 0<=a.capture<=a.frames:
        p.error("require frames >= 1 and 0 <= capture <= frames")
    try:
        manifest=json.loads(Path(str(a.dataset)+".json").read_text(encoding="utf-8"))
        digest=sha256(a.dataset)
        if digest!=manifest.get("sha256"):
            raise ValueError("replay hash differs from manifest")
        config=a.config or ("B" if family=="baseline" else "D")
        out=ROOT/family/"results"/a.run_name
        if out.exists():
            raise ValueError("output exists; choose a new run-name")
        cmd=command(ROOT/"build",config,a.dataset,out,a.frames,capture=a.capture)
        subprocess.run(cmd,check=True)
        if sha256(a.dataset)!=digest:
            raise ValueError("input changed during run")
        write_json(out/"run_context.json",{"family":family,"config":config,"dataset_sha256":digest,
                   "source_frames":manifest["count"],"executed_frames":a.frames,
                   "capture_frames":a.capture,"command":cmd,
                   "purpose":"single implementation demo; use run_review3.py for paired benchmarking"})
        print("Completed:",out)
        print("Raw captures and frame/worker/queue records are in this directory.")
        print("Use review3_demo.py for a joint HTML image/timeline viewer.")
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        p.exit(1,f"ERROR: {error}\n")

