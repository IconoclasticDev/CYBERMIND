#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cybermind.data.adapters.unified import UnifiedAdapter

SPECS={
 'CIC-IDS2018':'CIC-IDS2018','CIC-IDS2017':'CIC-IDS2017','UNSW-NB15':'UNSW-NB15','CTU-13':'CTU-13','CICIoT2023':'CICIoT2023'
}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True,choices=SPECS); ap.add_argument('--input',required=True); ap.add_argument('--output',required=True); ap.add_argument('--chunksize',type=int,default=250000); args=ap.parse_args()
    out_dir=Path(args.output); out_dir.mkdir(parents=True,exist_ok=True)
    files=sorted(Path(args.input).rglob('*.csv')) if Path(args.input).is_dir() else [Path(args.input)]
    adapter=UnifiedAdapter(SPECS[args.source]); reports=[]; written=[]
    for f in files:
        try:
            out,r=adapter.convert(f, chunksize=args.chunksize)
            if out.empty: continue
            try:
                import pyarrow  # noqa: F401
                dest=out_dir/(f.stem+'.parquet'); out.to_parquet(dest,index=False)
            except Exception:
                dest=out_dir/(f.stem+'.csv'); out.to_csv(dest,index=False)
            written.append(str(dest)); reports.append(r.__dict__)
            print(f'OK {f.name}: {len(out):,} rows -> {dest.name}')
        except Exception as e: print(f'SKIP {f}: {e}')
    (out_dir/'adapter_report.json').write_text(json.dumps({'source':args.source,'files':written,'reports':reports},indent=2))

if __name__=='__main__': main()
