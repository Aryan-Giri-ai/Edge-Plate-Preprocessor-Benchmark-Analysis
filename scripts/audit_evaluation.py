#!/usr/bin/env python3
"""Audit retained measurements; no source replay or executable is needed."""
import argparse
import csv
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path
from common import CONFIGS, ALGORITHM_IDS, fingerprints, write_json

def rows(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def output_csv(path, records):
    if records:
        with path.open('w', newline='', encoding='utf-8') as f:
            w=csv.DictWriter(f, fieldnames=list(records[0])); w.writeheader(); w.writerows(records)

def audit(folder):
    folder=Path(folder)
    info=json.loads((folder/'experiment.json').read_text())
    if not info.get('complete'): raise ValueError('Experiment incomplete')
    argparser=argparse.ArgumentParser(add_help=False)
    argparser.add_argument('--configs',nargs='+',default=list(CONFIGS))
    argparser.add_argument('--rates',nargs='+',type=float,default=[0])
    planned,_=argparser.parse_known_args(info['argv'][1:])
    expected_count=info['repeats']
    canonical=None; groups=defaultdict(list); stage_groups=defaultdict(list); queue_groups=defaultdict(list)
    run_audits=[]; identifiers=set(); settings_by_group={}
    for entry in info['runs']:
        dest=(folder/entry['path']).resolve()
        s=json.loads((dest/'summary.json').read_text())
        f=rows(dest/'frames.csv'); workers=rows(dest/'workers.csv'); queues=rows(dest/'queues.csv')
        checks=[]
        def check(name, okay):
            if not okay: raise ValueError(f"{entry['name']}: audit failed: {name}")
            checks.append(name)
        key=(entry['rate'],entry['config'],entry['block'])
        check('unique_rate_configuration_block',key not in identifiers); identifiers.add(key)
        name,allocation,traversal,capacity=CONFIGS[entry['config']]
        sequential=name=='edge_seq'
        expected_slots=1 if sequential else info['slots']
        check('successful_run',(dest/'SUCCESS').is_file() and entry['fingerprints_match'])
        check('same_numerical_work',s['algorithm_id']==info['algorithm_id']==ALGORITHM_IDS[info['profile']] and s['profile']==info['profile'] and s['edge_threshold']==(info['edge_threshold'] if info['profile']=='source' else -1))
        check('fixed_input_controls',s['frames']==info['frames']==len(f) and s['source_frames']==info['dataset_manifest']['count'] and s['width']==info['dataset_manifest']['width'] and s['height']==info['dataset_manifest']['height'] and s['rate']==entry['rate'] and s['io']==info['io'])
        check('ablation_matches_design',s['mode']==('sequential' if sequential else 'pipeline') and s['allocation']==allocation and s['traversal']==traversal and s['slot_count']==expected_slots and s['queue_capacity']==(0 if sequential else capacity))
        check('capture_off_and_no_reported_drop',s['capture_frames']==0 and s['dropped_frames']==0)
        check('allocation_accounting',s['timed_frame_array_allocations']==(3*s['frames'] if allocation=='dynamic' else 0) and s['setup_frame_array_allocations']==(1 if allocation=='dynamic' else 3*expected_slots+1))
        check('frame_array_bound',s['frame_buffer_bound_bytes']==(5*expected_slots+1)*s['width']*s['height'])
        check('no_invented_hardware_counters',s['hardware_counters'] is None)
        check('elapsed_fps_consistent',math.isclose(s['fps'],s['frames']/s['elapsed_s'],rel_tol=1e-8))
        fp=fingerprints(dest)
        check('cyclic_source_order',all(int(x['source_index'])==i%s['source_frames'] for i,x in enumerate(f)))
        if canonical is None: canonical=fp
        check('all_frame_fingerprints_match',fp==canonical)
        previous={}; events=[]; slots=set()
        for x in f:
            slot=int(x['slot_id']); slots.add(slot)
            if not 0<=slot<expected_slots: raise ValueError('Slot outside configured pool')
            times=[float(x[k]) for k in ['request_ms','admit_ms','fetch_begin_ms','fetch_end_ms','gray_begin_ms','gray_end_ms','sobel_begin_ms','sobel_end_ms','output_begin_ms','output_end_ms','done_ms']]
            if any(a>b+1e-6 for a,b in zip(times,times[1:])): raise ValueError('Frame stage order violated')
            if slot in previous and times[1]<previous[slot]-1e-6: raise ValueError('Slot overwritten before prior frame completion')
            previous[slot]=times[-1]
            for stage in ['fetch','gray','sobel','output']:
                begin=float(x[stage+'_begin_ms']);end=float(x[stage+'_end_ms'])
                events.extend([(begin,1),(end,-1)])
                if not math.isclose(end-begin,float(x[stage+'_ms']),rel_tol=1e-7,abs_tol=2e-5): raise ValueError('Stage duration inconsistent')
        active=maximum=0
        for _,delta in sorted(events): active+=delta; maximum=max(maximum,active)
        check('frame_stage_and_slot_order',True)
        check('stage_interval_overlap_bound',1<=maximum<=(1 if sequential else 4))
        thread_count=len({x['thread_id'] for x in workers})
        check('actual_worker_identifiers',len(workers)==4 and thread_count==(1 if sequential else 4))
        check('queue_set',set(x['queue'] for x in queues)==(set() if sequential else {'free_pool','Q1','Q2','Q3'}))
        for x in queues:
            cap=int(x['capacity']);mean=float(x['time_weighted_mean']);high=int(x['high_watermark'])
            check('bounded_'+x['queue'],cap==(expected_slots if x['queue']=='free_pool' else capacity) and 0<=mean<=high+1e-7 and high<=cap)
            queue_groups[(entry['rate'],entry['config'],x['queue'])].append(x)
        for x in workers:
            stage_groups[(entry['rate'],entry['config'],int(x['worker']))].append(x)
        settings_by_group[(entry['rate'],entry['config'])]=s
        groups[(entry['rate'],entry['config'])].append(entry['block'])
        run_audits.append(dict(name=entry['name'],config=entry['config'],rate=entry['rate'],block=entry['block'],checks=len(checks),frames=len(f),distinct_sources=len({x[0] for x in fp}),worker_ids=thread_count,max_stage_wall_overlap=maximum,slots_used=len(slots),elapsed_s=s['elapsed_s'],passed=True))
    for key,blocks in groups.items():
        if sorted(blocks)!=list(range(1,expected_count+1)): raise ValueError('Missing or duplicate block: '+str(key))
    if set(groups)!={(rate,config) for rate in planned.rates for config in planned.configs}:
        raise ValueError('Measured groups differ from planned command')
    rate_configs=defaultdict(set)
    for rate,config in groups: rate_configs[rate].add(config)
    if len({tuple(sorted(c)) for c in rate_configs.values()})!=1: raise ValueError('Unequal configuration coverage across rates')
    stages=[]
    for (rate,config,worker),items in sorted(stage_groups.items()):
        row=dict(rate=rate,config=config,worker=worker,runs=len(items))
        for metric in ['service_s','cv_input_wait_s','cv_output_wait_s','cv_stall_pct','cpu_s','cpu_one_core_pct','pace_sleep_s']:
            values=[float(x[metric]) for x in items if x[metric]!='']
            row[metric+'_median']=st.median(values) if values else ''
        stages.append(row)
    queue_rows=[]
    for (rate,config,queue),items in sorted(queue_groups.items()):
        queue_rows.append(dict(rate=rate,config=config,queue=queue,capacity=int(items[0]['capacity']),time_weighted_mean_median=st.median(float(x['time_weighted_mean']) for x in items),high_watermark_max=max(int(x['high_watermark']) for x in items)))
    output_csv(folder/'audit_runs.csv',run_audits);output_csv(folder/'audit_workers.csv',stages);output_csv(folder/'audit_queues.csv',queue_rows)
    result={'passed':True,'runs_audited':len(run_audits),'frames_audited':sum(x['frames'] for x in run_audits),'unique_source_images':info['dataset_manifest']['count'],'minimum_run_s':min(x['elapsed_s'] for x in run_audits),'fingerprint_scope':'source index, sum and weighted sum; non-cryptographic and not full-byte equality for every timed frame','stronger_correctness_evidence':'Run scripts/check.py for independent reference checks, tests/check_capture.py for captured-plane equality, and review3_demo.py for dataset-specific full-byte captures','checks':'completion, paired blocks, numerical/configuration controls, frame/source/stage/slot ordering, allocation counts, actual worker IDs, queue bounds, interval overlap, FPS arithmetic, all-frame fingerprint equality','limits':['No new source-image execution by this audit','No hardware performance counters','No learned model or accuracy measurement','Source/binary hashes are retained provenance; compiled binaries and private dataset replays are excluded from the portable evidence package']}
    write_json(folder/'audit.json',result)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('experiment',type=Path)
    print(json.dumps(audit(parser.parse_args().experiment),indent=2))
