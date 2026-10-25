#!/usr/bin/env python3
"""Initialize both deterministic programs on each official UFPR partition."""
import argparse,sys
from pathlib import Path
from common import ROOT,write_json
from prepare_ufpr import prepare
from run_model import execute
from compare_runs import compare

def main():
    p=argparse.ArgumentParser(description=__doc__)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--dataset-root',type=Path)
    source.add_argument('--prepared',type=Path)
    p.add_argument('--run-name',required=True)
    p.add_argument('--limit-per-split',type=int,default=60)
    p.add_argument('--allow-partial',action='store_true')
    p.add_argument('--capture',type=int,default=4)
    a=p.parse_args()
    if a.limit_per_split<0 or a.capture<0:p.error('limit/capture must be nonnegative')
    if not a.run_name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in a.run_name):p.error('Use letters/digits/_/- for run-name')
    result=ROOT/'results'/a.run_name
    if result.exists() or any((ROOT/f/'results'/a.run_name).exists() for f in ['baseline','pipeline']):p.error('Run name already used')
    prepared=a.prepared or ROOT/'data/prepared'/a.run_name
    if a.dataset_root:prepare(a.dataset_root,prepared,a.limit_per_split,a.allow_partial)
    result.mkdir(parents=True)
    status={'complete':False,'training_status':'not_applicable_deterministic_preprocessor','prepared':str(prepared),'splits':{}}
    write_json(result/'initialization.json',status)
    for split in ['training','validation','testing']:
        b=execute('baseline',prepared,split,a.run_name,capture=a.capture)
        d=execute('pipeline',prepared,split,a.run_name,capture=a.capture)
        matched=compare(b,d,result/split)
        status['splits'][split]={'frames':matched['frames'],'capture_frames':matched['captured_frames'],'equality':'passed'}
        write_json(result/'initialization.json',status)
    status['complete']=True;write_json(result/'initialization.json',status)
    print('Initialized both programs. No model was fitted. Results:',result)
if __name__=='__main__':main()
