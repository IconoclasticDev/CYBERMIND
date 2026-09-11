from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import torch
from .types import GraphState
from .pcap_extract import PACKET_FEATURES
from .stages import UNKNOWN_STAGE

NODE_FEATURE_NAMES = [
    'packet_count','flow_count','bytes_total','packets_total','unique_peer_count',
    'unique_dst_port_count','tcp_ratio','udp_ratio','mean_duration','mean_iat',
    'bytes_per_flow','packets_per_flow','activity_rate','anomaly_proxy'
] + list(PACKET_FEATURES)
EDGE_FEATURE_NAMES = ['bytes','packets','protocol','port','direction','duration','inter_arrival'] + list(PACKET_FEATURES)

def _packet_values(frame):
    """Missing packet telemetry stays explicit rather than being invented from flow data."""
    return [float(pd.to_numeric(frame[name], errors='coerce').fillna(0).mean())
            if name in frame and len(frame) else 0.0
            for name in list(PACKET_FEATURES)]

def _aggregate_node_features(g: pd.DataFrame, nodes: List[str]) -> np.ndarray:
    feats = []
    total_rows = max(len(g), 1)
    for node in nodes:
        as_src = g[g.src == node]
        as_dst = g[g.dst == node]
        both = pd.concat([as_src, as_dst], ignore_index=True)
        packet_count = float(both.packets_fwd.sum() + both.packets_bwd.sum())
        flow_count = float(len(both))
        bytes_total = float(both.bytes_fwd.sum() + both.bytes_bwd.sum())
        packets_total = packet_count
        peer = set(both.src.astype(str)) | set(both.dst.astype(str))
        peer.discard(node)
        dst_ports = set(pd.concat([as_src.dst_port, as_dst.dst_port]).astype(int).tolist()) if len(both) else set()
        proto = both.protocol.astype(float)
        tcp_ratio = float((proto == 6).mean()) if len(proto) else 0.0
        udp_ratio = float((proto == 17).mean()) if len(proto) else 0.0
        mean_duration = float(both.duration.mean()) if len(both) else 0.0
        mean_iat = float(pd.concat([both.mean_fwd_iat, both.mean_bwd_iat]).mean()) if len(both) else 0.0
        bytes_per_flow = bytes_total / max(flow_count, 1.0)
        packets_per_flow = packets_total / max(flow_count, 1.0)
        activity_rate = flow_count / total_rows
        # Cheap anomaly proxy: log-volume + unique-peer pressure. Not a trained anomaly detector.
        anomaly_proxy = float(np.tanh(np.log1p(flow_count) / 4.0 + len(peer) / 10.0))
        feats.append([
            packet_count, flow_count, bytes_total, packets_total, len(peer), len(dst_ports),
            tcp_ratio, udp_ratio, mean_duration, mean_iat, bytes_per_flow, packets_per_flow,
            activity_rate, anomaly_proxy
        ] + _packet_values(both))
    return np.nan_to_num(np.asarray(feats, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)

def _aggregate_edges(g: pd.DataFrame, node_to_idx: Dict[str, int]):
    pair = defaultdict(lambda: {'bytes':0., 'packets':0., 'protocol':0., 'port':0., 'duration':0., 'iat':0., 'n':0.})
    for r in g.itertuples(index=False):
        s, d = str(r.src), str(r.dst)
        if s not in node_to_idx or d not in node_to_idx or s == '' or d == '':
            continue
        k = (node_to_idx[s], node_to_idx[d])
        e = pair[k]
        e['bytes'] += float(r.bytes_fwd + r.bytes_bwd)
        e['packets'] += float(r.packets_fwd + r.packets_bwd)
        e['protocol'] += float(r.protocol)
        e['port'] += float(r.dst_port)
        e['duration'] += float(r.duration)
        e['iat'] += float((r.mean_fwd_iat + r.mean_bwd_iat) / 2.0)
        e['n'] += 1
        for name in list(PACKET_FEATURES):
            e[name] = e.get(name, 0.) + float(getattr(r, name, 0.))
    edges, attrs = [], []
    for (s,d), e in pair.items():
        n = max(e['n'],1.)
        edges.append([s,d])
        attrs.append([e['bytes'],e['packets'],e['protocol']/n,e['port']/n,1.,e['duration']/n,e['iat']/n] +
                     [e.get(name, 0.)/n for name in list(PACKET_FEATURES)])
    if not edges:
        return torch.zeros((2,0),dtype=torch.long), torch.zeros((0,len(EDGE_FEATURE_NAMES)),dtype=torch.float32)
    return torch.tensor(edges,dtype=torch.long).t().contiguous(), torch.tensor(attrs,dtype=torch.float32)

def build_graph_state(window: pd.DataFrame, scenario_id: str, metadata: dict, normalizer=None) -> GraphState:
    nodes = sorted(set(window.src.astype(str)) | set(window.dst.astype(str)))
    nodes = [n for n in nodes if n and n.lower() != 'nan']
    if len(nodes) == 0:
        raise ValueError('No endpoint identities available for graph construction.')
    node_to_idx = {n:i for i,n in enumerate(nodes)}
    x = torch.tensor(_aggregate_node_features(window, nodes),dtype=torch.float32)
    edge_index, edge_attr = _aggregate_edges(window, node_to_idx)
    metadata = dict(metadata)
    if normalizer is None and metadata.get('normalization_path'):
        from .normalization import FeatureNormalizer
        normalizer = FeatureNormalizer.load(metadata['normalization_path'])
    if normalizer is not None:
        x = normalizer.transform(x, 'node')
        edge_attr = normalizer.transform(edge_attr, 'edge')
        metadata['normalization_fingerprint'] = normalizer.fingerprint
    label_counts = window.label.value_counts()
    attack_label = str(label_counts.index[0]) if len(label_counts) else 'BENIGN'
    # The head predicts whether infiltration is present in a window, not the
    # fraction of attack flows. Mixed windows must remain valid binary targets.
    infil = float((window.infiltration > 0).any()) if len(window) else 0.0
    # Class IDs are categorical: averaging them invents a stage never observed.
    stages = window.loc[window.infiltration > 0, 'stage'].value_counts()
    stage = (int(stages.index[0]) if len(stages) == 1 or (len(stages) > 1 and stages.iloc[0] > stages.iloc[1])
             else UNKNOWN_STAGE) if len(stages) else 0
    ts = float(pd.Timestamp(window.timestamp.iloc[0]).timestamp()) if len(window) else 0.0
    return GraphState(x=x,edge_index=edge_index,edge_attr=edge_attr,node_ids=nodes,timestamp=ts,
                      y_infiltration=infil,y_stage=stage,scenario_id=scenario_id,attack_label=attack_label,
                      metadata=dict(metadata))
