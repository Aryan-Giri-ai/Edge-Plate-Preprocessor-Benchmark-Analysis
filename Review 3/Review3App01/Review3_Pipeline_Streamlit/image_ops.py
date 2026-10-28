import io
import numpy as np
from PIL import Image

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


def png_bytes(a):
    buf=io.BytesIO();Image.fromarray(a).save(buf,format="PNG");return buf.getvalue()
