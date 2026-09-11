from __future__ import annotations
from typing import Iterable, List
import pandas as pd
from .types import GraphSequenceSample
from .graph_builder import build_graph_state

def make_sequences(df: pd.DataFrame, scenario_id: str, window_seconds: float=60.0, history: int=8,
                   stride_seconds: float=60.0, metadata: dict|None=None) -> List[GraphSequenceSample]:
    if df.empty:
        return []
    data = df.sort_values('timestamp').copy()
    data['epoch'] = data.timestamp.astype('int64') / 1e9
    start = float(data.epoch.min())
    end = float(data.epoch.max())
    states = []
    t = start
    while t <= end + 1e-6:
        w = data[(data.epoch >= t) & (data.epoch < t + window_seconds)]
        if len(w):
            states.append(build_graph_state(w, scenario_id, metadata or {}))
        t += stride_seconds
    samples=[]
    for i in range(max(0,len(states)-history+1)):
        seq=states[i:i+history]
        if len(seq)>=2:
            samples.append(GraphSequenceSample(states=seq,scenario_id=scenario_id,start_time=seq[0].timestamp,
                                               window_seconds=window_seconds,metadata=metadata or {}))
    return samples
