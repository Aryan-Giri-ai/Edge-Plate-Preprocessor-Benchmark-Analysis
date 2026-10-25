#!/usr/bin/env python3
"""Run A, B and D and create an offline Review 2 report from measured captures."""
import argparse
import csv
import html
import json
import platform
import os
import struct
import subprocess
import sys
from pathlib import Path
from common import ROOT, ALGORITHM_IDS, command, fingerprints, sha256, write_json

STAGES = ['fetch', 'gray', 'sobel', 'output']
NAMES = ['Fetch', 'Gray / contrast', 'Sobel + binary closing', 'Output / recycle']

def rows(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def schedule_check(frames, summary):
    last_by_stage = [-1.0]*4
    last_by_slot = {}
    events=[]
    for r in frames:
        previous=float(r['admit_ms'])
        for i,stage in enumerate(STAGES):
            start,end=float(r[stage+'_begin_ms']),float(r[stage+'_end_ms'])
            if start+1e-7<previous or end<start or start+1e-7<last_by_stage[i]:
                raise ValueError('Stage order or same-worker overlap violation')
            previous=end;last_by_stage[i]=end
            if end>start: events.extend([(start,1),(end,-1)])
        slot=int(r['slot_id'])
        if not 0<=slot<summary['slot_count']:
            raise ValueError('Invalid slot identity')
        if float(r['fetch_begin_ms'])+1e-7<last_by_slot.get(slot,-1):
            raise ValueError('Slot reused before previous output finished')
        last_by_slot[slot]=float(r['output_end_ms'])
    active=peak=0
    for _,change in sorted(events):
        active+=change;peak=max(peak,active)
    if summary['mode']=='sequential' and peak!=1:
        raise ValueError('Sequential intervals unexpectedly overlap')
    return {'max_overlapping_stage_intervals':peak,'unique_slots_used':len(last_by_slot),
            'order_and_slot_reuse_check':'passed',
            'interpretation':'Wall-interval overlap includes possible preemption; it is not simultaneous CPU instruction execution.'}

def table(headers, data):
    esc=lambda v:html.escape(str(v))
    return '<table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in data)+'</tbody></table>'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--build',type=Path,default=ROOT/'build')
    p.add_argument('--frames',type=int,default=120)
    p.add_argument('--capture',type=int,default=8)
    p.add_argument('--edge-threshold',type=int,default=80)
    a=p.parse_args()
    if a.out.exists() or not 1<=a.capture<=a.frames<=1000000 or not 0<=a.edge_threshold<=1020:
        p.error('out must be new; require 1 <= capture <= frames <= 1000000; threshold 0..1020')
    from PIL import Image,ImageChops
    manifest=json.loads(Path(str(a.dataset)+'.json').read_text(encoding='utf-8'))
    digest=sha256(a.dataset)
    if digest!=manifest.get('sha256'): raise ValueError('Dataset hash differs from manifest')
    for c in ['A','B','D']: command(a.build,c,a.dataset,a.out,a.frames)
    a.out.mkdir(parents=True)
    report={'dataset_sha256':digest,'dataset_manifest':manifest,'platform':platform.platform(),
            'algorithm_id':ALGORITHM_IDS['source'],'edge_threshold':a.edge_threshold,
            'purpose':'Captured demonstration; do not use its FPS for the final performance conclusion.',
            'runs':{},'complete':False}
    base=None;captured=None
    run_dirs={c:ROOT/('baseline' if c in {'A','B'} else 'pipeline')/'results'/a.out.name/c for c in ['A','B','D']}
    for c in ['A','B','D']:
        dest=run_dirs[c]
        subprocess.run(command(a.build,c,a.dataset,dest,a.frames,capture=a.capture,
                               edge_threshold=a.edge_threshold),check=True,timeout=600)
        summary=json.loads((dest/'summary.json').read_text())
        if summary.get('algorithm_id')!=ALGORITHM_IDS['source']:
            raise ValueError('Stale executable; rebuild')
        fp=fingerprints(dest);edges=(dest/'captured_edges.raw').read_bytes()
        if base is None: base=fp;captured=edges
        elif fp!=base or edges!=captured: raise ValueError('Output mismatch: demo rejected')
        fr=rows(dest/'frames.csv');workers=rows(dest/'workers.csv')
        ids={w['thread_id'] for w in workers}
        if len(ids)!=(4 if c=='D' else 1): raise ValueError('Unexpected worker identity count')
        check=schedule_check(fr,summary)
        report['runs'][c]={'summary':summary,'frames':fr,'workers':workers,'queues':rows(dest/'queues.csv'),'relative_path':Path(os.path.relpath(dest,a.out)).as_posix(),**check}
        print(f"{c}: {len(ids)} thread ID(s), interval overlap maximum {check['max_overlapping_stage_intervals']}, "
              f"{check['unique_slots_used']} slots used, ordered slot reuse PASS")
    if sha256(a.dataset)!=digest: raise ValueError('Dataset changed during demo')
    w,h=report['runs']['B']['summary']['width'],report['runs']['B']['summary']['height'];n=w*h
    gray=(run_dirs['B']/'captured_gray.raw').read_bytes()
    d_edges=(run_dirs['D']/'captured_edges.raw').read_bytes()
    pics=a.out/'images';pics.mkdir()
    with a.dataset.open('rb') as f:
        for i in range(a.capture):
            f.seek(20+(i%manifest['count'])*3*n)
            inp=Image.frombytes('RGB',(w,h),f.read(3*n))
            g=Image.frombytes('L',(w,h),gray[i*n:(i+1)*n])
            b=Image.frombytes('L',(w,h),captured[i*n:(i+1)*n])
            d=Image.frombytes('L',(w,h),d_edges[i*n:(i+1)*n])
            for key,img in [('input',inp),('gray',g),('baseline',b),('pipeline',d),('difference',ImageChops.difference(b,d))]:
                img.save(pics/f'{i:03d}_{key}.png')
    report['capture_byte_equality']='A, B and D: passed'
    report['complete']=True
    write_json(a.out/'demo.json',report)
    content=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Review 2 | Edge preprocessing</title>',
    '<style>body{font:16px system-ui;margin:0;background:#f3f5f8;color:#172433}main{max-width:1200px;margin:auto;padding:28px}h1{font-size:32px}h2{margin-top:34px}p{line-height:1.6}.notice{background:#fff0c2;padding:16px;border-left:5px solid #997000}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card,section{background:white;padding:14px;border-radius:8px}.card img{width:100%;height:180px;object-fit:contain;background:#111}table{border-collapse:collapse;width:100%;font-size:14px;margin:16px 0}td,th{text-align:left;padding:9px;border-bottom:1px solid #ccd3de}th{background:#e3e9f0}.scroll{overflow:auto}canvas{width:100%;height:250px;background:#fff}code{overflow-wrap:anywhere}label{display:block;margin:16px 0}.sub{color:#4d6075}a{color:#005ba8} @media(max-width:750px){.cards{grid-template-columns:1fr 1fr}}</style><main>',
    '<h1>Review 2: edge preprocessing</h1>',
    '<p class="notice">'+html.escape(report['purpose'])+' Input kind: <b>'+html.escape(manifest['kind'])+'</b>. '+('Generated noise, ramps and stripes are not traffic-camera evidence.' if manifest['kind']=='synthetic' else 'Converted images retain original dimensions; inspect the manifest for the selection.')+'</p>',
    '<p>CPU-only C++20. A: sequential with dynamic arrays. B: sequential with reused arrays. D: four workers with a reusable 34-slot pool and queue capacity 5. All run the same algorithm and frame order.</p>',
    '<p><b>Algorithm:</b> RGB grayscale + fixed contrast → vertical Sobel → binary threshold '+str(a.edge_threshold)+' → 3×3 closing → output. Chen et al. (2024), §4.4, supplies Sobel/threshold/closing; US6553131B1 Fig. 1 block 16 supplies vertical-edge prior art. No plate detector, segmentation, SVM or OCR is implemented.</p>',
    '<p>Input: '+str(w)+' × '+str(h)+'; '+str(manifest['count'])+' source frames replayed for '+str(a.frames)+' frames. SHA-256: <code>'+digest+'</code>. OS: '+html.escape(report['platform'])+'</p>',
    '<h2>Visible outputs</h2><p>Full-byte comparison of the captured A/B/D outputs: <b>PASS</b>. Frame fingerprints also match across the complete run. Images below come from the replay and the actual C++ captures. A and B outputs are identical.</p>',
    '<label>Captured frame <input id="frame" type="range" min="0" max="'+str(a.capture-1)+'" value="0"> <b id="frameLabel">0</b></label><div class="cards">']
    for key,label in [('input','Input RGB'),('gray','Captured gray / contrast'),('baseline','A / B sequential edge output'),('pipeline','D pipeline edge output'),('difference','Absolute B–D difference (black = equal)')]:
        content.append(f'<div class="card"><b>{label}</b><a data-kind="{key}" href="images/000_{key}.png"><img data-kind="{key}" src="images/000_{key}.png" alt="{label}"></a></div>')
    content+=['</div><h2>Actual recorded stage intervals</h2><p>Each bar is a measured service interval, colored by frame ID. The frame selector highlights the same frame across workers. The timeline is measured wall time, including possible preemption; it is not a CPU-core trace. Runs use separate time origins and scales. No synthetic animation is used.</p>',
              '<label>Run <select id="run"><option>A</option><option>B</option><option selected>D</option></select> First frame <input id="first" type="number" min="0" max="'+str(max(0,a.frames-1))+'" value="0"> Window: up to 16 frames</label><canvas id="timeline" width="1200" height="250"></canvas><p id="timelineInfo" class="sub"></p>',
              '<h2>Measured demo metrics</h2><p>Capture adds copies. Use benchmark.py with capture disabled for the final repeated experiment. 100% process CPU means one CPU-equivalent second per wall second.</p>']
    data=[]
    for c,r in report['runs'].items():
        s=r['summary']
        data.append([c,f"{s['fps']:.2f}",*[f"{s[k]:.3f}" for k in ['latency_p50_ms','latency_p95_ms','latency_p99_ms']],
                     f"{s['process_cpu_one_core_pct']:.1f}" if s['process_cpu_one_core_pct'] is not None else 'unavailable',
                     f"{s['peak_process_rss_mib']:.1f}" if s['peak_process_rss_mib'] is not None else 'unavailable',s['timed_frame_array_allocations'],r['max_overlapping_stage_intervals']])
    content.append('<div class="scroll">'+table(['Run','FPS','P50 ms','P95 ms','P99 ms','CPU %','Peak MiB','Timed array allocations','Max interval overlap'],data)+'</div>')
    for c,r in report['runs'].items():
        content.append('<h2>'+c+': stages and queues</h2>')
        content.append(table(['Stage','Thread ID','Mean service ms','Input CV wait s','Output CV wait s','CV stall %'],[[NAMES[i],v['thread_id'],f"{r['summary']['mean_stage_ms'][i]:.4f}",v['cv_input_wait_s'],v['cv_output_wait_s'],v['cv_stall_pct']] for i,v in enumerate(r['workers'])]))
        content.append(table(['Queue','Capacity','Time-weighted mean','High water'],[[v[k] for k in ['queue','capacity','time_weighted_mean','high_watermark']] for v in r['queues']]))
        content.append('<p>Unique slots used: '+str(r['unique_slots_used'])+'. Stage ordering and slot reuse: PASS. <a href="'+r['relative_path']+'/frames.csv">Frame / slot timestamps</a> · <a href="'+r['relative_path']+'/workers.csv">Workers</a> · <a href="'+r['relative_path']+'/summary.json">Summary</a></p>')
    content+=['<h2>What this demonstrates</h2><p>Sequential execution, four worker identities, overlapping wall intervals where observed, ordered slot reuse, bounded queue occupancy, CV waits, and equivalent preprocessing outputs. Queues carry slot IDs. Output returns each slot to the free pool. A zero producer wait is a measured absence of that wait in this run; it must not be relabeled as observed backpressure.</p>',
              '<p>IPC, cycles, cache references/misses, bandwidth, energy and per-core concurrency: <b>not measured</b>. Recognition accuracy, full patent reproduction, live-camera deadlines and guaranteed speedup: <b>not established</b>. Use docs/REVIEW2_DEMO.md and docs/COMPARATIVE_ANALYSIS.md to complete the A–F ablations and conclusions.</p>',
              '<p><a href="demo.json">Complete demo record</a></p></main><script>const runs='+json.dumps(report['runs']).replace('<','\\u003c')+'; const names='+json.dumps(NAMES)+';',
              '''const frame=document.getElementById('frame'),first=document.getElementById('first'),run=document.getElementById('run');
function draw(){let list=runs[run.value].frames;let n=Math.max(0,Math.min(list.length-1,Number(first.value)||0));let subset=list.slice(n,n+16);let t0=+subset[0].fetch_begin_ms,t1=Math.max(...subset.map(r=>+r.output_end_ms));let c=document.getElementById('timeline'),ctx=c.getContext('2d');ctx.clearRect(0,0,c.width,c.height);let left=210,width=960;ctx.font='14px sans-serif';
const stages=['fetch','gray','sobel','output'];stages.forEach((s,i)=>{ctx.fillStyle='#172433';ctx.fillText(names[i],5,42+i*44);ctx.fillStyle='#e5ebf0';ctx.fillRect(left,22+i*44,width,28);subset.forEach(r=>{let x=left+(+r[s+'_begin_ms']-t0)/(t1-t0)*width,w=(+r[s+'_end_ms']-+r[s+'_begin_ms'])/(t1-t0)*width;ctx.fillStyle='hsl('+((+r.frame_id*47)%360)+' 65% 42%)';ctx.fillRect(x,22+i*44,Math.max(.6,w),28);if(+r.frame_id===+frame.value){ctx.strokeStyle='#111';ctx.lineWidth=2;ctx.strokeRect(x,22+i*44,Math.max(.6,w),28);}});});ctx.fillStyle='#172433';ctx.fillText(t0.toFixed(3)+' ms',left,228);ctx.fillText(t1.toFixed(3)+' ms',1040,228);document.getElementById('timelineInfo').textContent='Run '+run.value+' | frame IDs '+n+'–'+(n+subset.length-1)+' | recorded interval '+(t1-t0).toFixed(3)+' ms | full-run maximum interval overlap '+runs[run.value].max_overlapping_stage_intervals;}
frame.oninput=()=>{document.getElementById('frameLabel').textContent=frame.value;document.querySelectorAll('[data-kind]').forEach(e=>{let path='images/'+String(frame.value).padStart(3,'0')+'_'+e.dataset.kind+'.png';if(e.tagName==='IMG')e.src=path;else e.href=path;});draw();};first.oninput=draw;run.onchange=draw;draw();</script></html>''']
    (a.out/'index.html').write_text('\n'.join(content),encoding='utf-8')
    (a.out/'SUCCESS').write_text('complete\n')
    print('PASS: captured bytes and all-frame fingerprints match. Open '+str((a.out/'index.html').resolve()))

if __name__=='__main__':
    try: main()
    except (OSError,ValueError,RuntimeError,ImportError,subprocess.SubprocessError) as e:
        print('ERROR:',e,file=sys.stderr);sys.exit(1)
