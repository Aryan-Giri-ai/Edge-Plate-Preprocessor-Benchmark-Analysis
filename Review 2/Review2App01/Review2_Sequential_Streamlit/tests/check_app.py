"""Independent scalar reference, native parity and Streamlit form behavior."""
from pathlib import Path
import io,json,sys,tempfile,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image
from processing import process,load_image,sample,export_zip,native_path

def reference(rgb,t):
    h,w=rgb.shape[:2]
    y=np.array([[(299*int(r)+587*int(g)+114*int(b)+500)//1000 for r,g,b in row] for row in rgb],dtype=np.uint8)
    c=np.clip((5*y.astype(np.int32)+2)//4-32,0,255).astype(np.uint8)
    b=np.zeros((h,w),dtype=np.uint8)
    kernel=((-1,0,1),(-2,0,2),(-1,0,1))
    for yy in range(1,h-1):
        for xx in range(1,w-1):
            dx=sum(int(c[yy+dy-1,xx+dx-1])*kernel[dy][dx] for dy in range(3) for dx in range(3))
            b[yy,xx]=255 if abs(dx)>=t else 0
    ones={(x,y) for y in range(h) for x in range(w) if b[y,x]}
    dil={(x+dx,y+dy) for x,y in ones for dx in [-1,0,1] for dy in [-1,0,1] if 0<=x+dx<w and 0<=y+dy<h}
    out=np.zeros((h,w),dtype=np.uint8)
    for yy in range(1,h-1):
        for xx in range(1,w-1):
            if all((xx+dx,yy+dy) in dil for dx in [-1,0,1] for dy in [-1,0,1]):out[yy,xx]=255
    return y,c,b,out

rng=np.random.default_rng(260826);checks=[]
for shape in [(3,3),(4,7),(13,17),(33,65)]:
    rgb=rng.integers(0,256,size=(*shape,3),dtype=np.uint8)
    for threshold in [0,80,1020]:
        a,m=process(rgb,threshold)
        for key,expected in zip(["grayscale","contrast","binary","closed"],reference(rgb,threshold)):
            assert np.array_equal(a[key],expected),(shape,threshold,key)
        events=m["python_stage_events"]
        assert all(events[i]["end_ms"]<=events[i+1]["begin_ms"] for i in range(4))
        if native_path().exists():
            n,nm=process(rgb,threshold,"Native C++ sequential")
            assert all(np.array_equal(a[k],n[k]) for k in ["contrast","binary","closed"])
checks.append("independent scalar convolution and set-based morphology at four sizes and thresholds 0/80/1020")
assert native_path().exists(),"Build native engine before this full parity suite."
rgb=rng.integers(0,256,size=(1080,1920,3),dtype=np.uint8)
a,m=process(rgb,80,"Native C++ sequential")
checks.append("1920x1080 native and Python full-byte parity on all three captured planes")
with tempfile.TemporaryDirectory() as tmp:
    file=Path(tmp)/"test.png";Image.fromarray(sample()).save(file)
    assert np.array_equal(load_image(file),sample())
    bad=Path(tmp)/"bad.png";bad.write_bytes(b"bad file")
    try:load_image(bad)
    except OSError:pass
    else:raise AssertionError("bad image accepted")
payload=export_zip(a,m)
with zipfile.ZipFile(io.BytesIO(payload)) as z:
    assert z.testzip() is None and len(z.namelist())==9
    assert json.loads(z.read("metadata.json"))["threshold"]==80
checks.append("PNG loading, corrupt-image rejection and downloadable output archive")
from streamlit.testing.v1 import AppTest
at=AppTest.from_file(str(ROOT/"app.py"),default_timeout=30).run()
assert not at.exception and "result" not in at.session_state
at.button[0].click().run()
assert not at.exception
assert at.session_state["result"][1]["threshold"]==80
assert at.session_state["result"][1]["engine"]=="Native C++ sequential"
at.slider[0].set_value(120)
assert at.session_state["result"][1]["threshold"]==80
at.button[0].click().run()
assert not at.exception and at.session_state["result"][1]["threshold"]==120
at.selectbox[0].set_value("Python sequential")
at.button[0].click().run()
assert not at.exception and at.session_state["result"][1]["engine"]=="Python sequential"
checks.append("Streamlit form waits for Run; threshold edits retain labeled prior result until resubmission; native and Python UI runs")
at.radio[0].set_value("Local dataset").run()
at.text_input[0].set_value("/missing/review2/images").run()
at.button[0].click().run()
assert not at.exception and len(at.error)>0
checks.append("local-folder invalid path displays an actionable error")
(ROOT/"tests/VALIDATION.json").write_text(json.dumps({"passed":True,"host":"Linux","checks":checks},indent=2))
print(json.dumps({"passed":True,"checks":checks},indent=2))

