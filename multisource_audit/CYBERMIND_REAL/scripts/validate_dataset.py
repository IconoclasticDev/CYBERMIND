#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys,pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); ap.add_argument('--strict',action='store_true'); args=ap.parse_args()
    p=Path(args.input); files=sorted(p.rglob('*.parquet'))+sorted(p.rglob('*.csv')) if p.is_dir() else [p]
    report=[]; bad=0
    for f in files:
        try:
            df=pd.read_parquet(f) if f.suffix=='.parquet' else pd.read_csv(f,nrows=10000,low_memory=False)
            req=['timestamp','src','dst','label']; missing=[c for c in req if c not in df.columns]
            endpoint=int(((df.get('src','').astype(str)!='')&(df.get('dst','').astype(str)!='')).sum()) if all(c in df for c in ['src','dst']) else 0
            rec={'file':str(f),'rows_checked':len(df),'missing_required':missing,'usable_endpoint_rows':endpoint,'timestamp_nonnull':int(pd.to_datetime(df['timestamp'],errors='coerce').notna().sum()) if 'timestamp' in df else 0}
            if missing or (args.strict and endpoint==0): bad+=1
            report.append(rec); print(rec)
        except Exception as e: bad+=1; report.append({'file':str(f),'error':str(e)})
    (ROOT/'data/manifests'/'validation_report.json').write_text(json.dumps(report,indent=2)); raise SystemExit(1 if bad else 0)
if __name__=='__main__': main()
