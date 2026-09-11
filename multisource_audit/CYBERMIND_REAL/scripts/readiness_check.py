#!/usr/bin/env python3
from pathlib import Path
import json,sys,os
ROOT=Path(__file__).resolve().parents[1]
checks={
 'sources.yaml':ROOT/'configs/sources.yaml',
 'stage_mapping':ROOT/'knowledge/stage_mapping.yaml',
 'schema':ROOT/'data/manifests/schema.json',
 'train_script':ROOT/'scripts/train.py',
 'model':ROOT/'src/cybermind/models/world_model.py',
 'baseline':ROOT/'scripts/run_baseline.py',
 'eval':ROOT/'scripts/eval.py',
}
for k,p in checks.items(): print(f'[OK] {k}: {p.exists()}')
for k in ['train.pt','val.pt','test.pt']:
    p=ROOT/'data/processed'/k; print(f'[DATA] {k}: {p.exists()} ({p.stat().st_size if p.exists() else 0} bytes)')
inter=list((ROOT/'data/intermediate').rglob('*.parquet'))+list((ROOT/'data/intermediate').rglob('*.csv'))
print('[DATA] normalized files:',len(inter))
if not inter:
    print('NEXT: download/convert a real public dataset into data/intermediate/.')
else:
    print('NEXT: run strict validation + prepare_data, then GPU preflight.')
