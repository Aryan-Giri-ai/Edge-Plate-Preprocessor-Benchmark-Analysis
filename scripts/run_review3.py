#!/usr/bin/env python3
"""Benchmark baseline and pipeline together, audit evidence and print metrics."""
import argparse,csv,json,re,subprocess,sys
from pathlib import Path
from common import ROOT,CONFIGS
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--tag',required=True)
    p.add_argument('--frames',type=int,default=600)
    p.add_argument('--repeats',type=int,default=10)
    p.add_argument('--warmup',type=int,default=60)
    p.add_argument('--all-configs',action='store_true')
    p.add_argument('--io',choices=['file','ram'],default='file')
    a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',a.tag):p.error('tag must use letters, numbers, underscore or hyphen')
    out=ROOT/'results'/a.tag
    if any((ROOT/d/'results'/a.tag).exists() for d in ['baseline','pipeline']) or out.exists():p.error('tag exists; choose a new tag')
    configs=list(CONFIGS) if a.all_configs else ['B','D']
    cmd=[sys.executable,str(ROOT/'scripts/benchmark.py'),'--dataset',str(a.dataset.resolve()),'--out',str(out),'--frames',str(a.frames),'--repeats',str(a.repeats),'--warmup',str(a.warmup),'--configs',*configs,'--rates','0','--slots','34','--io',a.io]
    subprocess.run(cmd,check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/audit_evaluation.py'),str(out)],check=True)
    with (out/'aggregate.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    with (out/'comparisons.csv').open(newline='') as f:comparisons=list(csv.DictReader(f))
    primary=next(x for x in comparisons if x['baseline']=='B' and x['candidate']=='D')
    lines=['REVIEW 3 BASELINE AND PIPELINE BENCHMARK','Capture disabled; same input and numerical operators.',
           'Config  FPS median   P95 ms   P99 ms   Peak MiB   CPU %']
    for r in rows:
        lines.append(f"{r['config']:6s} {float(r['fps_median']):10.3f} {float(r['p95_ms_median']):8.3f} {float(r['p99_ms_median']):8.3f} {float(r['peak_rss_mib_median']):10.3f} {float(r['cpu_one_core_pct_median']):7.1f}")
    lines.append(f"Paired D/B speedup: {float(primary['paired_speedup']):.3f}")
    if primary['ci95_low']:lines.append(f"95% interval: {float(primary['ci95_low']):.3f} to {float(primary['ci95_high']):.3f}")
    lines+=['Interpretation: '+primary['conclusion'],'Audit: PASS. Read audit.json and raw worker/queue/frame records.',
            'CPU 100% = one CPU-equivalent; latency columns are medians of per-run percentiles.',
            'Replay frames are not additional distinct source images.']
    text='\n'.join(lines)+'\n';(out/'SUMMARY.txt').write_text(text,encoding='utf-8');print(text)
if __name__=='__main__':main()
