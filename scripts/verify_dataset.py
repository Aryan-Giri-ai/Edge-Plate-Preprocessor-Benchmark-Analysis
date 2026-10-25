#!/usr/bin/env python3
"""Compare full edge bytes across configurations on actual-size dataset frames."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from common import ROOT, CONFIGS, command, fingerprints, sha256, write_json

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--build",type=Path,default=ROOT/"build")
    p.add_argument("--frames",type=int,default=8)
    p.add_argument("--profile",choices=["source","legacy"],default="source")
    p.add_argument("--edge-threshold",type=int,default=80)
    a=p.parse_args()
    if a.frames<1 or a.out.exists(): p.error("frames must be positive and out must be new")
    a.out.mkdir(parents=True)
    baseline=None; identity=None; checked=[]
    with tempfile.TemporaryDirectory(prefix="edge_verify_") as temp:
        for config in CONFIGS:
            dest=Path(temp)/config
            subprocess.run(command(a.build,config,a.dataset,dest,a.frames,capture=a.frames,profile=a.profile,edge_threshold=a.edge_threshold),check=True,timeout=300)
            data=(dest/"captured_edges.raw").read_bytes()
            fp=fingerprints(dest)
            if baseline is None:
                baseline=data;identity=fp
                meta=json.loads((dest/"summary.json").read_text())
                w,h=meta["width"],meta["height"]
                (a.out/"first_edge.pgm").write_bytes(f"P5\n{w} {h}\n255\n".encode()+data[:w*h])
            elif data!=baseline or fp!=identity:
                raise RuntimeError(f"BYTE MISMATCH in {config}; benchmark comparison is invalid")
            checked.append(config)
    write_json(a.out/"verification.json",dict(status="passed",dataset_sha256=sha256(a.dataset),
               profile=a.profile,edge_threshold=a.edge_threshold,
               frames=a.frames,width=w,height=h,configurations=checked,
               method="Full byte comparison against A, independent scalar oracle checked separately by check.py"))
    print(f"PASS: all configurations have identical complete edge bytes for {a.frames} frames")

if __name__=="__main__": main()
