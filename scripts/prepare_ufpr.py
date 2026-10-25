#!/usr/bin/env python3
"""Audit official UFPR splits and prepare deterministic decoded RGB replay files."""
import argparse, collections, json, re, shutil, sys
from pathlib import Path
from PIL import Image
from common import ROOT, sha256, write_json
from prepare_data import write_raw

EXPECTED={'training':(1800,60),'validation':(900,30),'testing':(1800,60)}

def annotation(path,w,h):
    text=path.read_text(encoding='utf-8-sig')
    match=re.search(r'^corners:\s*(.+)$',text,re.M)
    if match:
        nums=[int(x) for x in re.findall(r'-?\d+',match.group(1))]
        if len(nums)!=8: raise ValueError(f'Expected four plate corners: {path}')
        pts=list(zip(nums[::2],nums[1::2]));x0=min(x for x,y in pts);y0=min(y for x,y in pts)
        x1=max(x for x,y in pts)+1;y1=max(y for x,y in pts)+1
    else:
        match=re.search(r'^position_plate:\s*(.+)$',text,re.M)
        nums=[int(x) for x in re.findall(r'-?\d+',match.group(1))] if match else []
        if len(nums)!=4: raise ValueError(f'Missing/invalid plate geometry: {path}')
        x0,y0,bw,bh=nums;x1=x0+bw;y1=y0+bh;pts=None
    if not (0<=x0<x1<=w and 0<=y0<y1<=h): raise ValueError(f'Plate bounds outside image: {path}')
    camera=re.search(r'^camera:\s*(.+)$',text,re.M)
    return {'plate_bbox_xyxy':[x0,y0,x1,y1],'corners':pts,'camera':camera.group(1).strip() if camera else 'unspecified'}

def audit(root,allow_partial):
    inventory={};seen_tracks=set();seen_names=set()
    for split,(count,tracks) in EXPECTED.items():
        folder=root/split
        if not folder.is_dir(): raise ValueError(f'Missing {folder}; choose the parent of training, validation and testing')
        imgs=sorted(folder.rglob('*.png'))
        txts=sorted(folder.rglob('*.txt'))
        if not imgs: raise ValueError(f'No PNG images in {folder}')
        split_tracks=set();items=[]
        for f in imgs:
            track=f.parent.name
            if not re.fullmatch(r'track\d{4}',track): raise ValueError(f'Unexpected track folder: {f}')
            if track in seen_tracks or f.name in seen_names: raise ValueError('Track/file overlap between splits')
            ann=f.with_suffix('.txt')
            if not ann.is_file(): raise ValueError(f'Missing annotation for {f}')
            with Image.open(f) as img:
                if img.format!='PNG' or img.size!=(1920,1080): raise ValueError(f'Expected 1920x1080 PNG: {f}')
                w,h=img.size
            items.append({'path':f,'annotation_path':ann,'track':track,**annotation(ann,w,h)})
            split_tracks.add(track)
        orphan=[f for f in txts if not f.with_suffix('.png').is_file()]
        if orphan: raise ValueError(f'Orphan annotations in {split}: {len(orphan)}')
        if not allow_partial and (len(imgs)!=count or len(split_tracks)!=tracks or any(n!=30 for n in collections.Counter(x['track'] for x in items).values())):
            raise ValueError(f'{split} is incomplete: {len(imgs)} images/{len(split_tracks)} tracks; expected {count}/{tracks}. Use --allow-partial only for a declared subset.')
        inventory[split]=items;seen_tracks.update(split_tracks);seen_names.update(f.name for f in imgs)
    return inventory

def select(items,limit):
    if not limit or limit>=len(items):return items
    # Spread across sorted tracks before taking further frames from any track.
    groups={}
    for item in items: groups.setdefault(item['track'],[]).append(item)
    tracks=sorted(groups)
    selected=[];depth=0
    if limit<len(tracks):
        tracks=[tracks[i*(len(tracks)-1)//max(1,limit-1)] for i in range(limit)]
    while len(selected)<limit:
        for track in tracks:
            group=groups[track]
            if depth<len(group): selected.append(group[depth])
            if len(selected)==limit:break
        depth+=1
    return sorted(selected,key=lambda x:x['path'].as_posix())

def prepare(root,out,limit=60,allow_partial=False):
    root=root.resolve();out=out.resolve()
    if out.exists():raise ValueError('Prepared output exists; choose a new directory')
    inventory=audit(root,allow_partial)
    choices={s:select(items,limit) for s,items in inventory.items()}
    required=sum(len(v)*1920*1080*3+20 for v in choices.values())
    parent=out.parent
    while not parent.exists():parent=parent.parent
    if shutil.disk_usage(parent).free<required+100*1024*1024:raise ValueError(f'Insufficient free space: need {required:,} replay bytes plus a 100 MiB reserve')
    out.mkdir(parents=True)
    audit_report={'schema':1,'dataset':'UFPR-ALPR','dataset_root':str(root),'training_status':'not_applicable_deterministic_preprocessor',
                  'allow_partial':allow_partial,'limit_per_split':limit,'metadata_audit_only_for_unselected_images':True,
                  'selection':'sorted track coverage, then additional frames per track; selected replay ordered by path',
                  'splits':{},'complete':False}
    write_json(out/'dataset_audit.json',audit_report)
    for split,chosen in choices.items():
        details=[]
        def frames():
            for i,item in enumerate(chosen):
                f=item['path'];ann=item['annotation_path']
                with Image.open(f) as img:rgb=img.convert('RGB').tobytes()
                details.append({'index':i,'path':f.relative_to(root).as_posix(),'source_sha256':sha256(f),'annotation_sha256':sha256(ann),
                                **{k:v for k,v in item.items() if k not in {'path','annotation_path'}}})
                yield rgb
        raw=out/(split+'.epraw');write_raw(raw,1920,1080,len(chosen),frames())
        manifest={'format':'EPRAW01','kind':'UFPR-ALPR','split':split,'width':1920,'height':1080,'count':len(chosen),
                  'available_images':len(inventory[split]),'available_tracks':len({x['track'] for x in inventory[split]}),
                  'selected':details,'sha256':sha256(raw),'file_bytes':raw.stat().st_size,
                  'source_root':str(root),'conversion':'Pillow RGB; full original dimensions; no crop, resize or augmentation',
                  'annotation_use':'provenance and ground-truth bbox diagnostics only; not fed to the C++ preprocessor'}
        write_json(str(raw)+'.json',manifest)
        audit_report['splits'][split]={k:manifest[k] for k in ['count','available_images','available_tracks','sha256','file_bytes']}
        print(f'{split}: audited {len(inventory[split])} images; prepared {len(chosen)}; {raw.stat().st_size:,} bytes',flush=True)
    audit_report['complete']=True;write_json(out/'dataset_audit.json',audit_report)
    return audit_report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset-root',type=Path,required=True)
    p.add_argument('--out',type=Path,default=ROOT/'data/prepared')
    p.add_argument('--limit-per-split',type=int,default=60,help='0 = all images in each original split')
    p.add_argument('--allow-partial',action='store_true')
    a=p.parse_args()
    if a.limit_per_split<0:p.error('limit must be nonnegative')
    prepare(a.dataset_root,a.out,a.limit_per_split,a.allow_partial)
if __name__=='__main__':
    try:main()
    except (OSError,ValueError) as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
