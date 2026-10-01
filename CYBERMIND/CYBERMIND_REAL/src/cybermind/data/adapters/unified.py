from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re
import pandas as pd
import numpy as np
from cybermind.data.stages import classify_stage
from cybermind.data.pcap_extract import PACKET_FEATURES


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
        src='src' if 'src' in df else pick(cols,'Source IP','Src IP','srcip')
        dst='dst' if 'dst' in df else pick(cols,'Destination IP','Dst IP','dstip')
        ts=pick(cols,'Timestamp','Time','Datetime','Date Time','ts')
        label=pick(cols,'Attack Category','attack_cat','Label','Class','Attack','category','type')
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
        if ts:
            text = df[ts].astype(str)
            # CICFlowMeter dates use day/month/year. Canonical ISO dates are
            # parsed separately so day-first cannot swap their month and day.
            day_first = text.str.match(r'^\d{1,2}/\d{1,2}/\d{4}') & self.source.startswith('CIC-IDS')
            parsed = pd.Series(pd.NaT, index=df.index, dtype='datetime64[ns, UTC]')
            parsed.loc[day_first] = pd.to_datetime(text[day_first], errors='coerce', dayfirst=True, format='mixed', utc=True)
            parsed.loc[~day_first] = pd.to_datetime(text[~day_first], errors='coerce', format='mixed', utc=True)
            o['timestamp'] = parsed
        else:
            o['timestamp'] = pd.NaT
        o['src']=df[src].astype(str) if src else ''
        o['dst']=df[dst].astype(str) if dst else ''
        for outcol,col in [('src_port',sp),('dst_port',dp),('protocol',proto),('duration',dur),('bytes_fwd',bf),('bytes_bwd',bb),('packets_fwd',pf),('packets_bwd',pb),('flow_bytes_s',fbytes),('flow_packets_s',fpkts),('mean_fwd_iat',mf),('mean_bwd_iat',mb)]:
            if outcol in df.columns:
                col = outcol
            o[outcol]=pd.to_numeric(df[col],errors='coerce').replace([np.inf, -np.inf], np.nan).fillna(0.0) if col else 0.0
        packet_valid = pd.Series(True, index=df.index)
        for column in PACKET_FEATURES:
            if column not in df:
                packet_valid[:] = False
            else:
                packet_valid &= np.isfinite(pd.to_numeric(df[column], errors='coerce'))
        if 'packet_features_available' in df:
            packet_valid &= pd.to_numeric(df['packet_features_available'], errors='coerce').eq(1)
        for column in PACKET_FEATURES:
            o[column] = pd.to_numeric(df[column], errors='coerce').replace([np.inf, -np.inf], np.nan).fillna(0.0) if column in df else 0.0
        o['packet_features_available'] = packet_valid.astype(float)
        o['label']=df[label].astype(str).str.strip().str.upper() if label else 'BENIGN'
        stage = 'attack_stage' if 'attack_stage' in df else ('stage' if 'stage' in df else None)
        o['attack_stage'] = (pd.to_numeric(df[stage], errors='coerce').fillna(o['label'].map(self._stage)).astype('int16')
                             if stage else o['label'].map(self._stage).astype('int16'))
        # Keep audited join evidence in the canonical corpus so strict
        # validation can still reject an unverified upstream label.
        for column in ('label_verified', 'label_refinement_verified', 'corrected_refinement_status',
                       'label_method', 'corrected_rule_source', 'original_rule_source',
                       'flow_feature_source', 'capture_date', 'capture_member',
                       'source_pcap_sha256'):
            if column in df:
                o[column] = df[column]
        o['source']=self.source
        if 'environment_id' in df:
            o['environment_id'] = df['environment_id']
        o['source_file']=str(getattr(df,'name',''))
        o=o[(o.src.notna())&(o.dst.notna())&(o.src.astype(str).str.lower()!='nan')&(o.dst.astype(str).str.lower()!='nan')]
        return o

    @staticmethod
    def _stage(label):
        return classify_stage(label)

    def _report(self,path,out):
        return AdapterReport(self.source,path.name,int(len(out)),int(len(out)),0,
            'endpoint_columns' if len(out) and (out.src.astype(str)!='').any() and (out.dst.astype(str)!='').any() else 'missing',
            'parsed_timestamp' if len(out) and out.timestamp.notna().any() else 'row_order_fallback',
            None,[])
