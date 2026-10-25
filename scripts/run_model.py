#!/usr/bin/env python3
"""Shared launcher for separate baseline and pipeline projects."""
import argparse,csv,html,json,platform,subprocess,sys
from pathlib import Path
from PIL import Image,ImageChops
from common import ROOT,ALGORITHM_IDS,command,sha256,write_json

def execute(family,prepared,split,tag,frames=0,capture=4,config=None):
    if family not in {'baseline','pipeline'}:raise ValueError('Invalid program')
    if not tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in tag):raise ValueError('run-name must use letters, digits, _ or -')
    prepared=Path(prepared).resolve()
    audit=json.loads((prepared/'dataset_audit.json').read_text())
    if not audit.get('complete'):raise ValueError('Dataset preparation is incomplete')
    data=prepared/(split+'.epraw');manifest=json.loads(Path(str(data)+'.json').read_text())
    if manifest.get('split')!=split or manifest.get('kind')!='UFPR-ALPR':raise ValueError('Wrong split/dataset manifest')
    digest=sha256(data)
    if digest!=manifest['sha256']:raise ValueError('Replay SHA-256 mismatch')
    settings=json.loads((ROOT/'config/project.json').read_text())
    n=frames or manifest['count'];capture=min(capture,n)
    chosen=config or ('B' if family=='baseline' else 'D')
    if chosen not in ({'A','B'} if family=='baseline' else {'C','D','E1','E3','F'}):raise ValueError('Config belongs to the other program')
    dest=ROOT/family/'results'/tag/split
    cmd=command(ROOT/'build',chosen,data,dest,n,slots=settings['slots'],capture=capture,
                profile=settings['profile'],edge_threshold=settings['edge_threshold'],io=settings['io'])
    subprocess.run(cmd,check=True,timeout=3600)
    summary=json.loads((dest/'summary.json').read_text())
    if summary.get('algorithm_id')!=settings['algorithm_id']:raise ValueError('Stale binary: rebuild')
    if sha256(data)!=digest:raise ValueError('Input changed during execution')
    context={'schema':1,'family':family,'config':chosen,'dataset':'UFPR-ALPR','split':split,
             'dataset_sha256':digest,'manifest_sha256':sha256(Path(str(data)+'.json')),
             'selected_source_frames':manifest['count'],'executed_frames':n,'capture_frames':capture,
             'algorithm_id':summary['algorithm_id'],'settings':settings,'platform':platform.platform(),
             'binary_sha256':sha256(cmd[0]),'command':cmd,'training_status':'not_applicable_deterministic_preprocessor',
             'purpose':'initialization and output assessment; captured runs are not primary benchmark timings'}
    write_json(dest/'run_context.json',context)
    if capture:render(dest,data,manifest,summary)
    (dest/'ASSESSMENT_SUCCESS').write_text('complete\n')
    return dest

def render(dest,data,manifest,summary):
    w,h=summary['width'],summary['height'];n=w*h;c=summary['capture_frames']
    gray=(dest/'captured_gray.raw').read_bytes();edges=(dest/'captured_edges.raw').read_bytes()
    if len(gray)!=c*n or len(edges)!=c*n:raise ValueError('Capture length mismatch')
    folder=dest/'images';folder.mkdir()
    diagnostics=[];cards=[]
    with data.open('rb') as stream:
        for i in range(c):
            selected=manifest['selected'][i%manifest['count']]
            stream.seek(20+(i%manifest['count'])*3*n)
            inp=Image.frombytes('RGB',(w,h),stream.read(3*n))
            g=Image.frombytes('L',(w,h),gray[i*n:(i+1)*n]);e=Image.frombytes('L',(w,h),edges[i*n:(i+1)*n])
            bbox=selected['plate_bbox_xyxy'];area=(bbox[2]-bbox[0])*(bbox[3]-bbox[1])
            total=n-e.histogram()[0];plate=area-e.crop(bbox).histogram()[0]
            diagnostics.append({'frame_id':i,'source_path':selected['path'],'track':selected['track'],
              'nonzero_fraction':total/n,'gt_plate_bbox_nonzero_fraction':plate/area,
              'outside_bbox_nonzero_fraction':(total-plate)/(n-area),
              'meaning':'edge occupancy only; GT box is supplied annotation, not a detected box; no accuracy claim'})
            for key,img in [('input',inp),('gray',g),('edge',e),('gt_plate_edge',e.crop(bbox))]:img.save(folder/f'{i:03d}_{key}.png')
            cards.append('<h2>Frame '+str(i)+' — '+html.escape(selected['path'])+'</h2><div class="grid">'+''.join('<figure><a href="images/'+f'{i:03d}_{key}.png"><img src="images/'+f'{i:03d}_{key}.png" alt="{label}"></a><figcaption>{label}</figcaption></figure>' for key,label in [('input','Input RGB'),('gray','Actual gray/contrast'),('edge','Actual closed edge output'),('gt_plate_edge','Edge crop using supplied ground-truth box')])+'</div>')
    with (dest/'output_diagnostics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(diagnostics[0]));writer.writeheader();writer.writerows(diagnostics)
    (dest/'outputs.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>UFPR preprocessing outputs</title><style>body{font:16px system-ui;max-width:1200px;margin:30px auto;padding:20px;color:#172433}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0}img{width:100%;height:260px;object-fit:contain;background:#eee}p{line-height:1.6}</style><h1>'+html.escape(summary['mode'])+' | UFPR '+manifest['split']+'</h1><p>Actual C++ captures. Ground-truth plate crops use dataset annotations after processing; this program does not predict a plate location or text. Click images for full resolution.</p><p>Algorithm: grayscale/contrast, vertical Sobel, binary threshold, 3×3 closing. Profile: source. These captured demonstration runs are excluded from the primary timing study.</p>'+''.join(cards)+'</html>',encoding='utf-8')

def main(family):
    p=argparse.ArgumentParser(description='Run '+family+' on one prepared official UFPR split')
    p.add_argument('--prepared',type=Path,default=ROOT/'data/prepared')
    p.add_argument('--split',choices=['training','validation','testing'],default='training')
    p.add_argument('--run-name',required=True)
    p.add_argument('--frames',type=int,default=0)
    p.add_argument('--capture',type=int,default=4)
    p.add_argument('--config',choices=['A','B'] if family=='baseline' else ['C','D','E1','E3','F'])
    a=p.parse_args()
    if a.frames<0 or a.capture<0:p.error('frames/capture must be nonnegative')
    try:print('Completed:',execute(family,a.prepared,a.split,a.run_name,a.frames,a.capture,a.config))
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
