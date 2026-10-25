#!/usr/bin/env python3
"""Run the measured thread demo and print the actual edge-stage trace."""
import argparse,json,subprocess,sys
from pathlib import Path
from PIL import Image,ImageChops
from common import ROOT,write_json

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--frames',type=int,default=120)
    p.add_argument('--capture',type=int,default=3)
    a=p.parse_args()
    subprocess.run([sys.executable,str(ROOT/'scripts/demo.py'),'--dataset',str(a.dataset),'--out',str(a.out),'--frames',str(a.frames),'--capture',str(a.capture)],check=True)
    demo=json.loads((a.out/'demo.json').read_text())
    metrics=[]
    for i in range(a.capture):
        with Image.open(a.out/f'images/{i:03d}_binary.png') as b,Image.open(a.out/f'images/{i:03d}_pipeline.png') as e:
            difference=ImageChops.difference(b,e)
            metrics.append(dict(frame_id=i,source_index=i%demo['dataset_manifest']['count'],binary_nonzero_pixels=b.histogram()[255],closed_nonzero_pixels=e.histogram()[255],changed_pixels=difference.histogram()[255]))
    report={'complete':True,'captures':metrics,'interpretation':'Nonzero/changed pixels describe the fixed edge transform; they are not accuracy or proof of better plate recognition. All four threads preserve the same numerical result.','capture_origin':'actual native Worker 3 pre-closing buffer; same point in sequential code','full_byte_equality':demo['capture_byte_equality']}
    write_json(a.out/'refinement.json',report)
    lines=['REVIEW 3 MEASURED THREAD AND EDGE DEMONSTRATION',
           'Capture is enabled. Use the separate capture-free benchmark for performance conclusions.',
           'W1 Fetch -> W2 Gray/contrast -> W3 Sobel/threshold/closing -> W4 Output/recycle.',
           'Workers overlap DIFFERENT frames. W3 alone runs the full edge stage for each frame.','']
    for config in ['A','B','D']:
        r=demo['runs'][config]
        lines.append(f"{config}: {len(set(x['thread_id'] for x in r['workers']))} actual thread IDs; max wall-interval overlap {r['max_overlapping_stage_intervals']}; slot-order audit {r['order_and_slot_reuse_check']}")
    r=demo['runs']['D'];lines+=['','Pipeline worker IDs (not CPU core numbers):']
    for w in r['workers']:lines.append(f"W{w['worker']}: {w['thread_id']}")
    lines+=['','First four pipeline frames, events sorted by measured start time:',
            'Frame Source Slot Worker       Begin ms       End ms']
    events=[]
    for f in r['frames'][:4]:
        for i,stage in enumerate(['fetch','gray','sobel','output'],1):
            events.append((float(f[stage+'_begin_ms']),float(f[stage+'_end_ms']),int(f['frame_id']),int(f['source_index']),int(f['slot_id']),i))
    for begin,end,frame,source,slot,worker in sorted(events):
        lines.append(f'{frame:5d} {source:6d} {slot:4d} W{worker:<5d} {begin:13.3f} {end:12.3f}')
    lines+=['','Captured edge transformations:']
    for m in metrics:lines.append(f"Frame {m['frame_id']}: binary pixels={m['binary_nonzero_pixels']}; closed pixels={m['closed_nonzero_pixels']}; changed={m['changed_pixels']}")
    lines+=['','PASS: '+demo['capture_byte_equality'],
            'Wall-time overlap includes possible preemption. No per-core execution trace is claimed.',
            'Open '+str((a.out/'index.html').resolve())]
    text='\n'.join(lines)+'\n';(a.out/'console.txt').write_text(text,encoding='utf-8');print(text)
if __name__=='__main__':main()
