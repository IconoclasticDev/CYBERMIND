"""CIC-IDS2018 tolerant feature extraction.

The converter handles common CIC-IDS2018 column spellings and records provenance.
It deliberately does not invent host identities or ATT&CK labels silently.
"""
from __future__ import annotations
import math, re
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple
import numpy as np
import pandas as pd

ATTACK_TO_STAGE = {
    'BENIGN': 0,
    'BRUTE FORCE -WEB': 1, 'BRUTE FORCE -XSS': 1, 'SQL INJECTION': 1,
    'INFILTRATION': 2,
    'BOT': 2, 'BOTNET': 2,
    'DOS ATTACK-HULK': 2, 'DOS ATTACK-GOLDENEYE': 2, 'DOS ATTACK-SLOWHTTPTEST': 2,
    'DOS ATTACK-SLOWLORIS': 2, 'DDOS ATTACK-HOIC': 2, 'DDOS ATTACK-LOIC-HTTP': 2,
    'DDOS ATTACK-LOIC-UDP': 2,
    'SSH-BRUTEFORCE': 1, 'FTP-BRUTEFORCE': 1,
    'HEARTBLEED': 2,
}

def norm_col(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(s).strip().lower())

def find_col(columns: Iterable[str], *candidates: str) -> Optional[str]:
    m = {norm_col(c): c for c in columns}
    for cand in candidates:
        if norm_col(cand) in m:
            return m[norm_col(cand)]
    return None

def find_contains(columns: Iterable[str], *tokens: str) -> Optional[str]:
    normalized = [(c, norm_col(c)) for c in columns]
    toks = [norm_col(t) for t in tokens]
    for c, n in normalized:
        if all(t in n for t in toks):
            return c
    return None

def infer_identity_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Dict[str, str]]:
    cols = list(df.columns)
    src = find_col(cols, 'Source IP', 'Src IP', 'SrcIP', 'Source')
    dst = find_col(cols, 'Destination IP', 'Dst IP', 'DstIP', 'Destination')
    meta = {'identity_method': 'endpoint_columns' if src and dst else 'missing'}
    return src, dst, meta

def canonical_label(v: object) -> str:
    if pd.isna(v):
        return 'BENIGN'
    return str(v).strip().upper()

def safe_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors='coerce').replace([np.inf, -np.inf], np.nan).fillna(0.0)

def extract_row_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, object]]:
    cols = list(df.columns)
    label_col = find_col(cols, 'Label', 'Class', 'Attack', 'Attack Category')
    if label_col is None:
        raise ValueError('Could not find a label column in CIC data.')
    src_col, dst_col, identity_meta = infer_identity_columns(df)
    protocol_col = find_col(cols, 'Protocol')
    src_port = find_col(cols, 'Source Port', 'Src Port', 'SrcPort')
    dst_port = find_col(cols, 'Destination Port', 'Dst Port', 'DstPort')
    time_col = find_col(cols, 'Timestamp', 'Time', 'Datetime', 'Date Time')
    duration_col = find_col(cols, 'Flow Duration', 'Duration')
    bytes_col = find_col(cols, 'Total Length of Fwd Packets', 'Total Fwd Packet Length', 'Fwd Packet Length Total')
    packets_fwd = find_col(cols, 'Total Fwd Packets', 'Fwd Packets/s', 'Fwd Packet/s')
    packets_bwd = find_col(cols, 'Total Backward Packets', 'Bwd Packets/s', 'Bwd Packet/s')
    bytes_fwd = find_col(cols, 'Total Length of Fwd Packets', 'Fwd Packet Length Total')
    bytes_bwd = find_col(cols, 'Total Length of Bwd Packets', 'Bwd Packet Length Total')
    mean_fwd = find_col(cols, 'Fwd IAT Mean')
    mean_bwd = find_col(cols, 'Bwd IAT Mean')
    flow_bytes_s = find_col(cols, 'Flow Bytes/s')
    flow_pkts_s = find_col(cols, 'Flow Packets/s')

    out = pd.DataFrame(index=df.index)
    if time_col:
        out['timestamp'] = pd.to_datetime(df[time_col], errors='coerce')
    else:
        out['timestamp'] = pd.NaT
    out['src'] = df[src_col].astype(str) if src_col else ''
    out['dst'] = df[dst_col].astype(str) if dst_col else ''
    out['protocol'] = safe_num(df[protocol_col]) if protocol_col else 0.0
    out['src_port'] = safe_num(df[src_port]) if src_port else 0.0
    out['dst_port'] = safe_num(df[dst_port]) if dst_port else 0.0
    out['duration'] = safe_num(df[duration_col]) if duration_col else 0.0
    out['bytes_fwd'] = safe_num(df[bytes_fwd]) if bytes_fwd else 0.0
    out['bytes_bwd'] = safe_num(df[bytes_bwd]) if bytes_bwd else 0.0
    out['packets_fwd'] = safe_num(df[packets_fwd]) if packets_fwd else 0.0
    out['packets_bwd'] = safe_num(df[packets_bwd]) if packets_bwd else 0.0
    out['mean_fwd_iat'] = safe_num(df[mean_fwd]) if mean_fwd else 0.0
    out['mean_bwd_iat'] = safe_num(df[mean_bwd]) if mean_bwd else 0.0
    out['flow_bytes_s'] = safe_num(df[flow_bytes_s]) if flow_bytes_s else 0.0
    out['flow_packets_s'] = safe_num(df[flow_pkts_s]) if flow_pkts_s else 0.0
    out['label'] = df[label_col].map(canonical_label)
    out['infiltration'] = (out['label'] != 'BENIGN').astype(np.float32)
    out['stage'] = out['label'].map(lambda x: ATTACK_TO_STAGE.get(x, 1 if x != 'BENIGN' else 0)).astype(int)
    if out['timestamp'].isna().all():
        # Preserve row order as pseudo-time only when timestamps are unavailable.
        out['timestamp'] = pd.to_datetime(np.arange(len(out)), unit='s')
    meta = {
        **identity_meta,
        'stage_method': 'heuristic_dataset_label_mapping',
        'label_column': label_col,
        'rows': int(len(out)),
    }
    return out, meta

def read_cic_csv(path: str | Path, chunksize: Optional[int] = None) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, nrows=None if chunksize is None else chunksize)
