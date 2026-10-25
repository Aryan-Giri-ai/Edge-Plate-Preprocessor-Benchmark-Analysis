"""Independent scalar check for the new pre-closing capture plane."""
import json,random,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from common import command
from prepare_data import write_raw
from check import reference
rng=random.Random(241026);w,h=17,13;rgb=rng.randbytes(w*h*3)
gray=bytes(max(0,min(255,(5*((299*rgb[i]+587*rgb[i+1]+114*rgb[i+2]+500)//1000)+2)//4-32)) for i in range(0,len(rgb),3))
binary=bytearray(w*h)
for y in range(1,h-1):
    for x in range(1,w-1):
        gradient=sum(gray[(y+dy)*w+x+dx]*weight for dy,dx,weight in [(-1,-1,-1),(-1,1,1),(0,-1,-2),(0,1,2),(1,-1,-1),(1,1,1)])
        binary[y*w+x]=255 if abs(gradient)>=80 else 0
with tempfile.TemporaryDirectory(prefix='review3_capture_') as tmp:
    root=Path(tmp);data=root/'input.epraw';write_raw(data,w,h,1,iter([rgb]))
    for c in ['A','B','D']:
        out=root/c;subprocess.run(command(ROOT/'build',c,data,out,3,capture=3),check=True,stdout=subprocess.DEVNULL)
        assert (out/'captured_gray.raw').read_bytes()==gray*3
        assert (out/'captured_binary.raw').read_bytes()==bytes(binary)*3
        assert (out/'captured_edges.raw').read_bytes()==reference(rgb,w,h)*3
report={'passed':True,'configs':['A','B','D'],'size':[w,h],'frames':3,'checks':['independent grayscale','independent thresholded vertical Sobel','independent set-based closing','three capture-plane lengths and offsets']}
(ROOT/'evidence').mkdir(exist_ok=True)
(ROOT/'evidence/review3_capture_test.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
