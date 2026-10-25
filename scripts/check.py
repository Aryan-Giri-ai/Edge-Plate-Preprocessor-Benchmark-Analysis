#!/usr/bin/env python3
"""Independent scalar reference, full-byte comparison and bounded-queue stress."""
import argparse
import csv
import json
import random
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from common import ROOT, CONFIGS, command, executable, fingerprints, write_json
from prepare_data import write_raw

def reference(rgb,w,h,profile="source",threshold=80):
    gray=[]
    for i in range(0,len(rgb),3):
        y=(299*rgb[i]+587*rgb[i+1]+114*rgb[i+2]+500)//1000
        gray.append(max(0,min(255,(5*y+2)//4-32)))
    gx=((-1,0,1),(-2,0,2),(-1,0,1))
    gy=((-1,-2,-1),(0,0,0),(1,2,1))
    out=bytearray(w*h)
    for y in range(1,h-1):
        for x in range(1,w-1):
            dx=dy=0
            for ky in range(3):
                for kx in range(3):
                    v=gray[(y+ky-1)*w+x+kx-1]
                    dx+=gx[ky][kx]*v; dy+=gy[ky][kx]*v
            strength=abs(dx) if profile=="source" else abs(dx)+abs(dy)
            out[y*w+x]=(255 if strength>=threshold else 0) if profile=="source" else min(255,strength)
    if profile=="source":
        # Independent set-based morphology: union neighborhoods, then containment.
        ones={(x,y) for y in range(h) for x in range(w) if out[y*w+x]}
        dilated={(x+dx,y+dy) for x,y in ones for dx in (-1,0,1) for dy in (-1,0,1)
                 if 0<=x+dx<w and 0<=y+dy<h}
        out=bytearray(w*h)
        for y in range(1,h-1):
            for x in range(1,w-1):
                if all((x+dx,y+dy) in dilated for dx in (-1,0,1) for dy in (-1,0,1)):
                    out[y*w+x]=255
    return bytes(out)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build",type=Path,default=ROOT/"build")
    p.add_argument("--report",type=Path)
    a=p.parse_args()
    log=[]
    def run(cmd,success=True):
        done=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
        if (done.returncode==0)!=success:
            raise RuntimeError(f"Unexpected exit {done.returncode}: {cmd}\n{done.stderr}")
        return done
    run([executable(a.build,"kernel_tests")]); log.append("hand-calculated kernel cases")
    rng=random.Random(260826)
    with tempfile.TemporaryDirectory(prefix="edge_check_") as temp:
        root=Path(temp)
        for w,h in [(3,3),(4,7),(17,13),(65,33)]:
            frames=[rng.randbytes(w*h*3) for _ in range(7)]
            data=root/f"{w}x{h}.epraw"; write_raw(data,w,h,len(frames),iter(frames))
            count=43
            for profile in ["source","legacy"]:
                golden=[reference(f,w,h,profile) for f in frames]
                expected=b"".join(golden[i%7] for i in range(count))
                for config in CONFIGS:
                    dest=root/f"{profile}_{w}x{h}_{config}"
                    run(command(a.build,config,data,dest,count,capture=count,profile=profile))
                    if (dest/"captured_edges.raw").read_bytes()!=expected:
                        raise RuntimeError(f"Independent reference mismatch: {profile} {w}x{h} {config}")
                    if len(fingerprints(dest))!=count: raise RuntimeError("frame count mismatch")
                    with (dest/"queues.csv").open(newline="") as f:
                        for row in csv.DictReader(f):
                            if not (0<=float(row["time_weighted_mean"])<=int(row["high_watermark"])<=int(row["capacity"])):
                                raise RuntimeError("queue bound failed")
                log.append(f"{profile} {w}x{h}: all 7 configurations, {count} frames, byte-exact independent reference")
        data=root/"65x33.epraw"
        golden=[reference(f,65,33) for f in frames]
        expected=b"".join(golden[i%7] for i in range(43))
        for slots in [1,4,34]:
            for allocation in ["pool","dynamic"]:
                dest=root/f"stress_{slots}_{allocation}"
                cmd=command(a.build,"D" if allocation=="pool" else "C",data,dest,501,slots=slots)
                cmd[cmd.index("--queue")+1]="1"
                run(cmd)
                if len(fingerprints(dest))!=501: raise RuntimeError("queue stress frame loss")
        log.append("queue capacity 1, slot pools 1/4/34, pool/dynamic, 501 frames each: no loss or timeout")
        for io in ["file","ram"]:
            dest=root/f"io_{io}"
            run(command(a.build,"D",data,dest,43,io=io,capture=43))
            if (dest/"captured_edges.raw").read_bytes()!=expected: raise RuntimeError("IO mode mismatch")
        log.append("file and RAM replay byte equality")
        for rate in [30,60]:
            dest=root/f"paced_{rate}"
            run(command(a.build,"D",data,dest,10,rate=rate,capture=10))
            if (dest/"captured_edges.raw").read_bytes()!=expected[:10*65*33]: raise RuntimeError("paced mismatch")
        log.append("30/60 FPS paced replay byte equality")
        for payload in [b"", b"EPRAW01\n"+struct.pack("<III",3,3,1),
                        b"EPRAW01\n"+struct.pack("<III",2,3,1)+bytes(18),
                        b"EPRAW01\n"+struct.pack("<III",3,3,1)+bytes(28)]:
            bad=root/"bad.epraw";bad.write_bytes(payload)
            run(command(a.build,"D",bad,root/"bad_output",1),False)
        for option,value in [("--queue","0"),("--slots","0"),("--rate","nan"),("--rate","-1"),("--frames","-1"),("--traversal","bad"),("--profile","unknown"),("--edge-threshold","1021")]:
            cmd=command(a.build,"D",data,root/"bad_option",1)
            cmd[cmd.index(option)+1]=value;run(cmd,False)
        run(command(a.build,"D",root/"absent.epraw",root/"absent",1),False)
        run(command(a.build,"D",data,root/"paced_30",1),False)
        log.append("missing/malformed/truncated/extra input, invalid options and output overwrite rejected")
        damaged=root/"runtime_damage.epraw"
        damaged.write_bytes(data.read_bytes())
        cmd=command(a.build,"D",damaged,root/"runtime_failure",10,rate=5)
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            time.sleep(.35)
            with damaged.open("r+b") as f: f.truncate(20)
            stdout,stderr=proc.communicate(timeout=10)
            if proc.returncode==0 or "frame read failed" not in stderr:
                raise RuntimeError(f"Runtime failure did not reach the expected error path: {stdout} {stderr}")
        finally:
            if proc.poll() is None: proc.kill(); proc.wait()
        log.append("input truncated during paced execution: worker failure cancels and joins all workers")
    for line in log: print("PASS:",line)
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        write_json(a.report,{"status":"passed","checks":log,"python":sys.version,"build":str(a.build.resolve())})

if __name__=="__main__":
    main()
