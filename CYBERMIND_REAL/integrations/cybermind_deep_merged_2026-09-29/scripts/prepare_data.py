#!/usr/bin/env python3
"""Turn normalized CYBERMIND parquet/CSV events into leakage-safe GraphSequenceSample splits."""
from pathlib import Path
import argparse,json,sys,math
import pandas as pd
import hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cybermind.data.temporal import make_sequences
from cybermind.data.dataset import save_dataset
from cybermind.data.graph_builder import build_graph_state
from cybermind.utils.config import load_config

ROOT=Path(__file__).resolve().parents[1]

def read_any(path):
    if path.suffix.lower()=='.parquet': return pd.read_parquet(path)
    return pd.read_csv(path,low_memory=False)

def canonicalize(df, source_file):
    required=['timestamp','src','dst','label']
    missing=[c for c in required if c not in df.columns]
    if missing: raise ValueError(f'{source_file}: missing {missing}')
    out=df.copy()
    out['timestamp']=pd.to_datetime(out['timestamp'],errors='coerce')
    if out['timestamp'].isna().all(): out['timestamp']=pd.to_datetime(range(len(out)),unit='s')
    out['src']=out['src'].astype(str); out['dst']=out['dst'].astype(str)
    out['label']=out['label'].astype(str).str.strip().str.upper()
    out['infiltration']=(out['label'].ne('BENIGN') & out['label'].ne('NORMAL')).astype('float32')
    if 'attack_stage' not in out.columns:
        out['stage']=out['label'].map(lambda x: 0 if x in ('BENIGN','NORMAL') else 1).astype('int16')
    else: out['stage']=pd.to_numeric(out['attack_stage'],errors='coerce').fillna(1).astype('int16')
    defaults={'protocol':0,'src_port':0,'dst_port':0,'duration':0,'bytes_fwd':0,'bytes_bwd':0,'packets_fwd':0,'packets_bwd':0,'mean_fwd_iat':0,'mean_bwd_iat':0,'flow_bytes_s':0,'flow_packets_s':0}
    for c,v in defaults.items():
        if c not in out: out[c]=v
        out[c]=pd.to_numeric(out[c],errors='coerce').fillna(0.0)
    return out

def split_ids(samples, seed):
    # Stable, source/scenario-aware split.
    groups=[]
    for s in samples:
        gid=str(s.metadata.get('source',''))+'::'+str(s.scenario_id)
        groups.append(gid)
    def key(x):
        return hashlib.sha256(f'{seed}::{x}'.encode()).hexdigest()
    uniq=sorted(set(groups), key=key)
    n=len(uniq)
    if n<3: return {'train':uniq[:max(1,n-2)],'val':uniq[max(0,n-2):max(1,n-1)],'test':uniq[max(1,n-1):]}
    a=max(1,int(n*.70)); b=max(a+1,int(n*.85))
    return {'train':uniq[:a],'val':uniq[a:b],'test':uniq[b:]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',required=True); ap.add_argument('--input',default='data/intermediate'); ap.add_argument('--strict',action='store_true'); args=ap.parse_args(); cfg=load_config(args.config)
    raw=ROOT/args.input; out=ROOT/cfg['data']['processed_dir']; out.mkdir(parents=True,exist_ok=True)
    files=sorted(list(raw.rglob('*.parquet'))+list(raw.rglob('*.csv')))
    if not files: raise SystemExit(f'No normalized data under {raw}. Run build_corpus.py first.')
    samples=[]; reports=[]
    for f in files:
        try:
            df=canonicalize(read_any(f),f.name)
            if args.strict and ((df.src=='')|(df.dst=='')).all(): raise ValueError('strict mode: no endpoint identities')
            scenario=f.parent.name+'__'+f.stem
            meta={'source':str(df.source.iloc[0]) if 'source' in df and len(df) else 'unknown','source_file':f.name,'endpoint_method':'columns','stage_method':'coarse_label_mapping'}
            seqs=make_sequences(df,scenario,window_seconds=cfg['data']['window_seconds'],history=cfg['data']['history'],stride_seconds=cfg['data']['stride_seconds'],metadata=meta)
            samples.extend(seqs); reports.append({'file':str(f),'rows':len(df),'samples':len(seqs),**meta})
            print(f'OK {f.name}: {len(df):,} rows -> {len(seqs):,} sequences')
        except Exception as e: print('SKIP',f,e)
    groups=split_ids(samples,cfg.get('seed',42)); splits={k:[] for k in groups}
    unique_groups=set(groups['train']+groups['val']+groups['test'])
    if len(unique_groups)<3:
        # Fallback for a single scenario/file: chronological sample split avoids future->past leakage.
        ordered=sorted(samples,key=lambda x:(x.start_time,x.scenario_id))
        n=len(ordered); a=max(1,int(n*.70)); b=max(a+1,int(n*.85)); splits={'train':ordered[:a],'val':ordered[a:b],'test':ordered[b:]}
        groups={'train':['<chronological-split>'],'val':['<chronological-split>'],'test':['<chronological-split>']}
    else:
        for s in samples:
            gid=str(s.metadata.get('source',''))+'::'+str(s.scenario_id)
            k='train' if gid in groups['train'] else 'val' if gid in groups['val'] else 'test'
            splits[k].append(s)
    for k,v in splits.items(): save_dataset(v,out/f'{k}.pt'); print(k,len(v))
    meta={'reports':reports,'split_groups':groups,'num_sequences':len(samples)}
    (out/'metadata.json').write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta,indent=2))
if __name__=='__main__': main()
