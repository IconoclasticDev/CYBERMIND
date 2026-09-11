from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re
import pandas as pd
import numpy as np


def norm(s): return re.sub(r'[^a-z0-9]+','',str(s).strip().lower())

def pick(cols, *names):
    m={norm(c):c for c in cols}
    for n in names:
        if norm(n) in m: return m[norm(n)]
    for c in cols:
        nc=norm(c)
        if any(norm(n) in nc for n in names): return c
    return None

@dataclass
class AdapterReport:
    source: str
    file: str
    rows_in: int
    rows_out: int
    dropped: int
    endpoint_method: str
    timestamp_method: str
    label_column: Optional[str]
    warnings: list[str]

class UnifiedAdapter:
    """Normalize common tabular cyber datasets into CYBERMIND's event schema."""
    def __init__(self, source: str): self.source=source

    def convert(self, path: str|Path, output: str|Path|None=None, chunksize: int|None=None):
        path=Path(path)
        if chunksize:
            parts=[]
            for chunk in pd.read_csv(path, low_memory=False, chunksize=chunksize): parts.append(self._convert_df(chunk))
            out=pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        else:
            out=self._convert_df(pd.read_csv(path, low_memory=False))
        report=self._report(path, out)
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            out.to_parquet(output, index=False) if str(output).endswith('.parquet') else out.to_csv(output,index=False)
        return out, report

    def _convert_df(self, df):
        cols=list(df.columns)
        src=pick(cols,'Source IP','Src IP','srcip','source','src')
        dst=pick(cols,'Destination IP','Dst IP','dstip','destination','dst')
        ts=pick(cols,'Timestamp','Time','Datetime','Date Time','ts')
        label=pick(cols,'Label','Class','Attack','Attack Category','category','type')
        sp=pick(cols,'Source Port','Src Port','src_port','sport')
        dp=pick(cols,'Destination Port','Dst Port','dst_port','dport')
        proto=pick(cols,'Protocol','Protocol Type','proto')
        dur=pick(cols,'Flow Duration','Duration','dur')
        bf=pick(cols,'Total Length of Fwd Packets','Total Fwd Packet Length','Bytes Fwd','tot_l_fw_pkt')
        bb=pick(cols,'Total Length of Bwd Packets','Total Bwd Packet Length','Bytes Bwd','tot_l_bw_pkt')
        pf=pick(cols,'Total Fwd Packets','Packets Fwd','tot_fw_pk')
        pb=pick(cols,'Total Backward Packets','Packets Bwd','tot_bw_pk')
        fbytes=pick(cols,'Flow Bytes/s','Bytes/s','Rate')
        fpkts=pick(cols,'Flow Packets/s','Packets/s','Srate')
        mf=pick(cols,'Fwd IAT Mean','fw_iat_avg','Mean Fwd IAT')
        mb=pick(cols,'Bwd IAT Mean','bw_iat_avg','Mean Bwd IAT')
        o=pd.DataFrame(index=df.index)
        o['timestamp']=pd.to_datetime(df[ts],errors='coerce') if ts else pd.NaT
        o['src']=df[src].astype(str) if src else ''
        o['dst']=df[dst].astype(str) if dst else ''
        for outcol,col in [('src_port',sp),('dst_port',dp),('protocol',proto),('duration',dur),('bytes_fwd',bf),('bytes_bwd',bb),('packets_fwd',pf),('packets_bwd',pb),('flow_bytes_s',fbytes),('flow_packets_s',fpkts),('mean_fwd_iat',mf),('mean_bwd_iat',mb)]:
            o[outcol]=pd.to_numeric(df[col],errors='coerce').fillna(0.0) if col else 0.0
        o['label']=df[label].astype(str).str.strip().str.upper() if label else 'BENIGN'
        o['attack_stage']=o['label'].map(self._stage).astype('int16')
        o['source']=self.source
        o['source_file']=str(getattr(df,'name',''))
        o=o[(o.src.notna())&(o.dst.notna())&(o.src.astype(str).str.lower()!='nan')&(o.dst.astype(str).str.lower()!='nan')]
        return o

    @staticmethod
    def _stage(label):
        x=str(label).upper()
        if x=='BENIGN' or x=='NORMAL': return 0
        if any(k in x for k in ['SCAN','RECON','BRUTE','FUZZ','ANALYSIS','PROBE']): return 1
        if any(k in x for k in ['EXPLOIT','BACKDOOR','SHELLCODE','BOT','INFILTR','HEARTBLEED','MALWARE','MIRAI','SPOOF']): return 2
        if any(k in x for k in ['EXFIL','IMPACT','RANSOM','DOS','DDOS','WORM']): return 3
        return 1

    def _report(self,path,out):
        return AdapterReport(self.source,path.name,int(len(out)),int(len(out)),0,
            'endpoint_columns' if len(out) and (out.src.astype(str)!='').any() and (out.dst.astype(str)!='').any() else 'missing',
            'parsed_timestamp' if len(out) and out.timestamp.notna().any() else 'row_order_fallback',
            None,[])
