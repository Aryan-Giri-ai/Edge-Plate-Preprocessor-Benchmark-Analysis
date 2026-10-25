#!/usr/bin/env python3
from pathlib import Path
import hashlib
root=Path(__file__).resolve().parents[1]
count=0
for line in (root/'MANIFEST_SHA256.txt').read_text().splitlines():
    expected,name=line.split('  ',1);p=root/name
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise SystemExit('FAIL: '+name)
    count+=1
print(f'PASS: {count} packaged file hashes')
