#!/usr/bin/env python3
"""Validate matched initialization runs and report measured demo metrics."""
import argparse,csv,json,sys
from pathlib import Path
from common import fingerprints,write_json

def compare(base,pipe,out):
    base=Path(base);pipe=Path(pipe);out=Path(out)
    if out.exists():raise ValueError('Comparison output exists')
    for p in [base,pipe]:
        if not (p/'ASSESSMENT_SUCCESS').is_file():raise ValueError('Missing assessment success marker')
    contexts=[json.loads((p/'run_context.json').read_text()) for p in [base,pipe]]
    summaries=[json.loads((p/'summary.json').read_text()) for p in [base,pipe]]
    for key in ['dataset_sha256','manifest_sha256','split','executed_frames','algorithm_id','capture_frames','settings']:
        if contexts[0][key]!=contexts[1][key]:raise ValueError('Unmatched input/configuration: '+key)
    for key in ['profile','edge_threshold','frames','rate','io','traversal','allocation']:
        if summaries[0][key]!=summaries[1][key]:raise ValueError('Unmatched numerical/measurement control: '+key)
    if summaries[0]['mode']!='sequential' or summaries[1]['mode']!='pipeline':raise ValueError('Expected sequential and pipeline pair')
    if fingerprints(base)!=fingerprints(pipe):raise ValueError('Output frame/fingerprint mismatch')
    capture=contexts[0]['capture_frames']
    if capture:
        for name in ['captured_gray.raw','captured_edges.raw']:
            if (base/name).read_bytes()!=(pipe/name).read_bytes():raise ValueError('Full captured byte mismatch: '+name)
    data={'status':'passed','split':contexts[0]['split'],'dataset_sha256':contexts[0]['dataset_sha256'],
          'frames':contexts[0]['executed_frames'],'captured_frames':capture,
          'all_frame_fingerprints_match':True,'captured_gray_and_edge_bytes_match':True if capture else None,
          'speedup_single_run':summaries[1]['fps']/summaries[0]['fps'],
          'interpretation':'initialization check, no repeated-run performance inference; capture adds work',
          'baseline':summaries[0],'pipeline':summaries[1]}
    out.mkdir(parents=True);write_json(out/'comparison.json',data)
    keys=['fps','latency_p50_ms','latency_p95_ms','latency_p99_ms','process_cpu_one_core_pct','peak_process_rss_mib','timed_frame_array_allocations']
    with (out/'metrics.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['metric','baseline','pipeline'])
        for k in keys:wr.writerow([k,summaries[0][k],summaries[1][k]])
    (out/'comparison.md').write_text('# UFPR initialization pair\n\nSplit: '+data['split']+'\n\nPASS: all-frame fingerprints and captured gray/edge bytes match.\n\nThis pair is a correctness/demo run, not repeated performance evidence.\n\n| Metric | Baseline | Pipeline |\n|:---|---:|---:|\n'+''.join(f'| {k} | {summaries[0][k]} | {summaries[1][k]} |\n' for k in keys)+'\nSingle-run FPS ratio: '+str(data['speedup_single_run'])+'; do not treat it as an established speedup.\n',encoding='utf-8')
    print('PASS matched '+data['split']+' pair -> '+str(out))
    return data

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--pipeline',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();compare(a.baseline,a.pipeline,a.out)
if __name__=='__main__':main()
