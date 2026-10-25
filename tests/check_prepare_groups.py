"""Check original-size grouping, source coverage and B/D output equivalence."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from common import command, fingerprints, sha256
from prepare_image_groups import prepare

with tempfile.TemporaryDirectory(prefix="edge_groups_") as directory:
    root=Path(directory); source=root/"input"; source.mkdir()
    specs=[("one.png",(17,13)),("two.png",(17,13)),("three.png",(19,15))]
    for i,(name,size) in enumerate(specs):
        Image.new("RGB",size,(30+40*i,90,160)).save(source/name)
    result=prepare(source,root/"prepared")
    assert result["complete"] and result["selected_images"]==3
    assert sorted(g["count"] for g in result["groups"])==[1,2]
    seen=[]
    for group in result["groups"]:
        replay=root/"prepared"/group["replay"]
        manifest=json.loads(Path(str(replay)+".json").read_text())
        assert manifest["sha256"]==sha256(replay)
        assert replay.stat().st_size==20+3*group["width"]*group["height"]*group["count"]
        with replay.open("rb") as stream:
            assert stream.read(8)==b"EPRAW01\n"
            assert struct.unpack("<III",stream.read(12))==(group["width"],group["height"],group["count"])
        seen += [x["path"] for x in manifest["selected"]]
        runs=[]
        for config in ["B","D"]:
            out=root/f"{group['width']}_{config}"
            subprocess.run(command(ROOT/"build",config,replay,out,7,capture=7),
                           check=True,stdout=subprocess.DEVNULL)
            runs.append(out)
        assert fingerprints(runs[0])==fingerprints(runs[1])
        for plane in ["gray","binary","edges"]:
            assert (runs[0]/f"captured_{plane}.raw").read_bytes()==(runs[1]/f"captured_{plane}.raw").read_bytes()
    assert sorted(seen)==sorted(x[0] for x in specs)
    limited=prepare(source,root/"limited",1)
    assert limited["selected_images"]==1
    for input_path,output_path in [(source,root/"prepared"),(source,source/"bad")]:
        try:
            prepare(input_path,output_path)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid or existing output was accepted")
print("PASS: native-size groups, source coverage, hashes, byte counts, B/D capture equality and output guards")

