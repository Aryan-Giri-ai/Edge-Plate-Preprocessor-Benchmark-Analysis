#!/usr/bin/env python3
"""Create a conventional uncompressed ZIP, manifest and download checksum."""
import argparse,hashlib,json,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def selected(p):
    r=p.relative_to(ROOT)
    if not p.is_file() or any(x in {'build','__pycache__','review2_authoring'} for x in r.parts):return False
    if p.name=='MANIFEST_SHA256.txt' or p.suffix in {'.epraw','.raw','.o','.exe','.pyc','.zip'}:return False
    if r.parts[0] in {'baseline','pipeline'} and ('images' in r.parts or p.name=='outputs.html'):return False
    return True
def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',type=Path,default=ROOT.parent/'Edge_Plate_UFPR_Project.zip');args=a.parse_args()
    if args.out.exists():a.error('Archive destination already exists; use a new --out')
    files=sorted(p for p in ROOT.rglob('*') if selected(p))
    manifest=ROOT/'MANIFEST_SHA256.txt'
    manifest.write_text(''.join(digest(p)+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files),encoding='utf-8')
    files.append(manifest)
    with zipfile.ZipFile(args.out,'w',compression=zipfile.ZIP_STORED,allowZip64=False) as z:
        for p in files:z.write(p,ROOT.name+'/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(args.out) as z:
        if z.testzip() is not None:raise RuntimeError('ZIP CRC check failed')
        if len(z.namelist())!=len(set(z.namelist())):raise RuntimeError('Duplicate member name')
        with tempfile.TemporaryDirectory(prefix='edge_zip_check_') as d:
            z.extractall(d)
            subprocess.run([sys.executable,str(Path(d)/ROOT.name/'scripts/check_package.py')],check=True)
    sha=digest(args.out)
    Path(str(args.out)+'.sha256').write_text(sha+'  '+args.out.name+'\n')
    print(json.dumps({'archive':str(args.out.resolve()),'files':len(files),'bytes':args.out.stat().st_size,'sha256':sha,'zip_crc':'passed','extracted_manifest':'passed'},indent=2))
if __name__=='__main__':main()
