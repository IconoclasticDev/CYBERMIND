from __future__ import annotations
from typing import Iterable, List
import numpy as np
import pandas as pd
from .types import GraphSequenceSample
from .graph_builder import build_graph_state

def make_sequences(df: pd.DataFrame, scenario_id: str, window_seconds: float=60.0, history: int=8,
                   stride_seconds: float=60.0, metadata: dict|None=None, normalizer=None) -> List[GraphSequenceSample]:
    if df.empty:
        return []
    if window_seconds <= 0 or stride_seconds <= 0 or history < 2:
        raise ValueError('Positive window/stride and history >= 2 are required')
    data = df.sort_values('timestamp', kind='stable').copy()
    data['epoch'] = pd.to_datetime(data.timestamp, utc=True).astype('datetime64[ns, UTC]').astype('int64') / 1e9
    epochs = data.epoch.to_numpy(dtype=float)
    start = float(data.epoch.min())
    end = float(data.epoch.max())
    states = []
    t = start
    while t <= end + 1e-6:
        left = int(np.searchsorted(epochs, t, side='left'))
        right = int(np.searchsorted(epochs, t + window_seconds, side='left'))
        if right > left:
            w = data.iloc[left:right]
            meta = {**(metadata or {}), 'window_start': t, 'window_end': t + window_seconds}
            states.append(build_graph_state(w, scenario_id, meta, normalizer=normalizer))
        t += stride_seconds
    samples=[]
    # Empty intervals delimit independent histories. Without this split, the
    # last state of one capture day can become adjacent to the first state of a
    # later day merely because empty windows were omitted.
    runs=[]
    for state in states:
        if (not runs or not runs[-1] or
                state.metadata['window_start'] - runs[-1][-1].metadata['window_start'] <= stride_seconds + 1e-6):
            if not runs:
                runs.append([])
            runs[-1].append(state)
        else:
            runs.append([state])
    for run in runs:
        for i in range(max(0,len(run)-history+1)):
            seq=run[i:i+history]
            if len(seq)>=2:
                samples.append(GraphSequenceSample(states=seq,scenario_id=scenario_id,start_time=seq[0].timestamp,
                                                   window_seconds=window_seconds,metadata=metadata or {}))
    return samples
