"""Sequential transforms matching the project's source profile."""
from pathlib import Path
from time import perf_counter
import csv, hashlib, io, json, os, struct, subprocess, tempfile, threading, zipfile
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent

def sample():
    yy,xx=np.indices((360,640))
    v=np.where(((xx//14)%2)==0,220,30).astype(np.uint8)
    return np.stack([v,((xx+yy)%256).astype(np.uint8),v],axis=2)

def load_image(source):
    with Image.open(source) as im:
        w,h=im.size
        if min(w,h)<3 or max(w,h)>8192 or w*h>12_000_000:
            raise ValueError("Use 3x3 pixels or larger, up to 12 megapixels and 8192 pixels per side.")
        return np.asarray(im.convert("RGB"),dtype=np.uint8).copy()

def luminance(rgb):
    a=rgb.astype(np.int32)
    return ((299*a[:,:,0]+587*a[:,:,1]+114*a[:,:,2]+500)//1000).astype(np.uint8)

def contrast(y):
    return np.clip((5*y.astype(np.int32)+2)//4-32,0,255).astype(np.uint8)

def gradient(gray):
    a=gray.astype(np.int32);gx=np.zeros(gray.shape,dtype=np.int32)
    gx[1:-1,1:-1]=(-a[:-2,:-2]+a[:-2,2:]-2*a[1:-1,:-2]+2*a[1:-1,2:]
                       -a[2:,:-2]+a[2:,2:])
    return np.abs(gx)

def threshold_map(g,t):
    out=np.where(g>=t,255,0).astype(np.uint8)
    out[0,:]=out[-1,:]=0;out[:,0]=out[:,-1]=0
    return out

def close_map(binary):
    h,w=binary.shape;a=np.pad(binary,1,constant_values=0)
    dilated=np.maximum.reduce([a[dy:dy+h,dx:dx+w] for dy in range(3) for dx in range(3)])
    a=np.pad(dilated,1,constant_values=0)
    return np.minimum.reduce([a[dy:dy+h,dx:dx+w] for dy in range(3) for dx in range(3)])

def native_path():
    return ROOT/"native"/"bin"/("edge_seq.exe" if os.name=="nt" else "edge_seq")

def native_run(rgb,t):
    exe=native_path()
    if not exe.is_file():
        raise FileNotFoundError("Native engine is not built. Use Python sequential or follow the native-engine setup.")
    h,w=rgb.shape[:2]
    with tempfile.TemporaryDirectory(prefix="review2_native_") as temp:
        root=Path(temp);source=root/"input.epraw";dest=root/"output"
        source.write_bytes(b"EPRAW01\n"+struct.pack("<III",w,h,1)+rgb.tobytes())
        cmd=[str(exe),"--input",str(source),"--out",str(dest),"--frames","1",
             "--allocation","pool","--traversal","row","--capture","1",
             "--profile","source","--edge-threshold",str(t)]
        done=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
        if done.returncode:
            raise RuntimeError("Native engine failed: "+(done.stderr or done.stdout or str(done.returncode))+
                               ". On Windows, put the UCRT64 bin directory on PATH.")
        if not (dest/"SUCCESS").exists():raise RuntimeError("Native run did not publish SUCCESS.")
        planes={key:np.frombuffer((dest/file).read_bytes(),dtype=np.uint8).reshape(h,w).copy()
                for key,file in {"contrast":"captured_gray.raw","binary":"captured_binary.raw",
                                 "closed":"captured_edges.raw"}.items()}
        summary=json.loads((dest/"summary.json").read_text())
        with (dest/"frames.csv").open(newline="") as f:frames=list(csv.DictReader(f))
        with (dest/"workers.csv").open(newline="") as f:workers=list(csv.DictReader(f))
        if summary["mode"]!="sequential" or len({r["thread_id"] for r in workers})!=1:
            raise RuntimeError("Expected one native sequential execution-thread identity.")
    return planes,summary,frames,workers

def process(rgb,t=80,engine="Python sequential"):
    if rgb.dtype!=np.uint8 or rgb.ndim!=3 or rgb.shape[2]!=3:raise ValueError("Expected RGB8.")
    if min(rgb.shape[:2])<3 or max(rgb.shape[:2])>8192 or rgb.shape[0]*rgb.shape[1]>12_000_000:
        raise ValueError("Unsupported image size.")
    if not 0<=t<=1020:raise ValueError("Threshold must be 0..1020.")
    arrays={"input":rgb.copy()};events=[];start=perf_counter()
    def stage(name,fn):
        begin=perf_counter();value=fn()
        events.append({"stage":name,"begin_ms":(begin-start)*1000,"end_ms":(perf_counter()-start)*1000})
        return value
    arrays["grayscale"]=stage("Grayscale",lambda:luminance(rgb))
    arrays["contrast"]=stage("Fixed contrast",lambda:contrast(arrays["grayscale"]))
    arrays["gradient"]=stage("Vertical Sobel",lambda:gradient(arrays["contrast"]))
    arrays["binary"]=stage("Binary threshold",lambda:threshold_map(arrays["gradient"],t))
    arrays["closed"]=stage("Morphological closing",lambda:close_map(arrays["binary"]))
    meta={"engine":engine,"threshold":t,"width":rgb.shape[1],"height":rgb.shape[0],
          "input_rgb_sha256":hashlib.sha256(rgb.tobytes()).hexdigest(),
          "final_sha256":hashlib.sha256(arrays["closed"].tobytes()).hexdigest(),
          "python_transform_ms":(perf_counter()-start)*1000,"python_execution_thread":str(threading.get_ident()),
          "source_profile":"chen-patent-edge-subset-v1","closing":"full 3x3 dilation then erosion",
          "borders":"zero Sobel outer border; zero outside morphology",
          "scope":"Single-frame demonstration, not baseline/pipeline benchmarking.","python_stage_events":events}
    if engine=="Native C++ sequential":
        planes,summary,frames,workers=native_run(rgb,t)
        if not all(np.array_equal(planes[k],arrays[k]) for k in planes):
            raise RuntimeError("Python/native pixel mismatch; result rejected.")
        arrays.update(planes)
        meta.update(native_summary=summary,native_frames=frames,native_workers=workers,
                    parity="Contrast grayscale, binary Sobel and final map match native bytes")
    arrays["gradient_preview"]=np.rint(arrays["gradient"]*(255/1020)).astype(np.uint8)
    arrays["closing_change"]=np.abs(arrays["closed"].astype(np.int16)-arrays["binary"]).astype(np.uint8)
    return arrays,meta

def png_bytes(a):
    buf=io.BytesIO();Image.fromarray(a).save(buf,format="PNG");return buf.getvalue()

def export_zip(arrays,meta):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
        for k in ["input","grayscale","contrast","gradient_preview","binary","closed","closing_change"]:
            z.writestr(k+".png",png_bytes(arrays[k]))
        z.writestr("metadata.json",json.dumps(meta,indent=2,allow_nan=False))
        g=io.BytesIO();np.save(g,arrays["gradient"]);z.writestr("sobel_response.npy",g.getvalue())
    return buf.getvalue()

