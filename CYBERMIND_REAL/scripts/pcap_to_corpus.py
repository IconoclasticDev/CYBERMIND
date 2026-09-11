#!/usr/bin/env python3
"""Recursively convert PCAP/PCAPNG captures to CYBERMIND flow rows with endpoint identity."""
from pathlib import Path
import argparse,json,sys
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cybermind.data.pcap_extract import pcap_to_dataframe

def infer_label(path: Path):
    x=path.stem.upper()
    if any(k in x for k in ['BENIGN','NORMAL']): return 'BENIGN'
    for k in ['DDOS','DOS','BOTNET','MIRAI','BRUTE','SCAN','RECON','INFILTRATION','HEARTBLEED','SQL','XSS','BACKDOOR','WORM']:
        if k in x: return k
    return 'PCAP_EVENT'

ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); ap.add_argument('--output',required=True); args=ap.parse_args()
outdir=Path(args.output); outdir.mkdir(parents=True,exist_ok=True); reports=[]
for f in sorted(Path(args.input).rglob('*')):
    if f.suffix.lower() not in ('.pcap','.pcapng','.cap'): continue
    try:
        label=infer_label(f); df=pcap_to_dataframe(f,label=label); df['source']='PCAP'; df['source_file']=str(f)
        dest=outdir/(f.stem+'.csv'); df.to_csv(dest,index=False); reports.append({'file':str(f),'rows':len(df),'label':label,'output':str(dest)})
        print('OK',f,'->',dest,len(df))
    except Exception as e: print('SKIP',f,e)
(outdir/'pcap_report.json').write_text(json.dumps(reports,indent=2))
