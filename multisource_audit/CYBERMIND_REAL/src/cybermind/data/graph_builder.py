from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import torch
from .types import GraphState

NODE_FEATURE_NAMES = [
    'packet_count','flow_count','bytes_total','packets_total','unique_peer_count',
    'unique_dst_port_count','tcp_ratio','udp_ratio','mean_duration','mean_iat',
    'bytes_per_flow','packets_per_flow','activity_rate','anomaly_proxy'
]
EDGE_FEATURE_NAMES = ['bytes','packets','protocol','port','direction','duration','inter_arrival']

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
        ])
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
    edges, attrs = [], []
    for (s,d), e in pair.items():
        n = max(e['n'],1.)
        edges.append([s,d])
        attrs.append([e['bytes'],e['packets'],e['protocol']/n,e['port']/n,1.,e['duration']/n,e['iat']/n])
    if not edges:
        return torch.zeros((2,0),dtype=torch.long), torch.zeros((0,len(EDGE_FEATURE_NAMES)),dtype=torch.float32)
    return torch.tensor(edges,dtype=torch.long).t().contiguous(), torch.tensor(attrs,dtype=torch.float32)

def build_graph_state(window: pd.DataFrame, scenario_id: str, metadata: dict) -> GraphState:
    nodes = sorted(set(window.src.astype(str)) | set(window.dst.astype(str)))
    nodes = [n for n in nodes if n and n.lower() != 'nan']
    if len(nodes) == 0:
        raise ValueError('No endpoint identities available for graph construction.')
    node_to_idx = {n:i for i,n in enumerate(nodes)}
    x = torch.tensor(_aggregate_node_features(window, nodes),dtype=torch.float32)
    edge_index, edge_attr = _aggregate_edges(window, node_to_idx)
    label_counts = window.label.value_counts()
    attack_label = str(label_counts.index[0]) if len(label_counts) else 'BENIGN'
    infil = float(window.infiltration.mean()) if len(window) else 0.0
    stage = int(round(float(window.stage.mean()))) if len(window) else 0
    ts = float(window.timestamp.astype('int64').iloc[0] / 1e9) if len(window) else 0.0
    return GraphState(x=x,edge_index=edge_index,edge_attr=edge_attr,node_ids=nodes,timestamp=ts,
                      y_infiltration=infil,y_stage=stage,scenario_id=scenario_id,attack_label=attack_label,
                      metadata=dict(metadata))
