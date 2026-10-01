from __future__ import annotations
from typing import Dict, Iterable, Sequence
import numpy as np
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, confusion_matrix

def binary_metrics(y_true,y_score,threshold=.5)->Dict[str,float|None]:
    y=np.asarray(y_true).astype(int); s=np.asarray(y_score); p=(s>=threshold).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,p,labels=[0,1]).ravel()
    fpr=fp/max(fp+tn,1)
    return {'f1':float(f1_score(y,p,zero_division=0)),'precision':float(precision_score(y,p,zero_division=0)),
            'recall':float(recall_score(y,p,zero_division=0)),'fpr':float(fpr),
            'ap':float(average_precision_score(y,s)) if len(np.unique(y))>1 else None}

def early_warning_lead_time(timestamps, y_true, risk_scores, threshold=.5, reliability_window=1):
    ts=np.asarray(timestamps,dtype=float); y=np.asarray(y_true).astype(int); s=np.asarray(risk_scores,dtype=float)
    critical=np.where(y>=1)[0]
    if critical.size==0: return {'lead_time_seconds':None,'warning_index':None,'critical_index':None}
    ci=int(critical[0]); warnings=np.where(s[:ci+1]>=threshold)[0]
    if warnings.size==0: return {'lead_time_seconds':0.0,'warning_index':None,'critical_index':ci}
    wi=int(warnings[0])
    return {'lead_time_seconds':float(max(0.,ts[ci]-ts[wi])),'warning_index':wi,'critical_index':ci}


def _as_numpy(value):
    if hasattr(value, 'detach'):
        value = value.detach().cpu().numpy()
    return np.asarray(value)


def illegal_transition_counts(stages, allowed_transitions=None, reset_mask=None,
                              mask=None, reset_transitions=None):
    """Count adjacent valid stage pairs, excluding explicitly allowed resets.

    Rows are independent sequences. Unknown exemption is encoded by the policy
    matrix. Padding requires a false mask (or the decode sentinel -1). Invalid
    non-padding IDs raise rather than silently improving the reported rate.
    """
    if allowed_transitions is None:
        from cybermind.models.stage_decoder import StageDecoder
        policy = StageDecoder()
        allowed_transitions = policy.allowed_transitions
        if reset_transitions is None:
            reset_transitions = policy.reset_transitions
    allowed = _as_numpy(allowed_transitions)
    if allowed.ndim != 2 or allowed.shape[0] != allowed.shape[1] or allowed.shape[0] == 0:
        raise ValueError('allowed_transitions must be a nonempty square matrix')
    if allowed.dtype != np.bool_:
        raise ValueError('allowed_transitions must be boolean')
    if reset_transitions is None:
        resets = np.zeros_like(allowed)
        for source in range(allowed.shape[0]):
            for destination in (0, 1):
                if destination < source and destination < allowed.shape[0]:
                    resets[source, destination] = not allowed[source, destination]
    else:
        resets = _as_numpy(reset_transitions)
        if resets.shape != allowed.shape or resets.dtype != np.bool_:
            raise ValueError('reset_transitions must be a matching boolean matrix')
        source, destination = np.indices(allowed.shape)
        if np.any(resets & ((destination >= source) | (destination > 1))):
            raise ValueError('resets may only enable backward transitions into stage 0 or 1')
    values = _as_numpy(stages)
    if values.ndim not in (1, 2):
        raise ValueError('stages must have shape [T] or [B,T]')
    if values.size == 0:
        values = values.astype(np.int64)
    if values.dtype.kind not in 'iu':
        raise ValueError('stages must contain integer IDs')
    valid = values != -1 if mask is None else _as_numpy(mask)
    reset = np.zeros_like(values, dtype=bool) if reset_mask is None else _as_numpy(reset_mask)
    for name, value in [('mask', valid), ('reset_mask', reset)]:
        if value.shape != values.shape or value.dtype != np.bool_:
            raise ValueError(f'{name} must be boolean with the same shape as stages')
    if np.any(valid & ((values < 0) | (values >= allowed.shape[0]))):
        raise ValueError('valid stages contain an out-of-range ID')
    if values.ndim == 1:
        values, valid, reset = values[None], valid[None], reset[None]
    pair_valid = valid[:, :-1] & valid[:, 1:]
    rows, times = np.where(pair_valid)
    previous, current = values[rows, times], values[rows, times + 1]
    base_legal = allowed[previous, current]
    actual_reset = reset[rows, times + 1] & resets[previous, current] & ~base_legal
    evaluated = ~actual_reset
    return {'illegal': int(np.count_nonzero(evaluated & ~base_legal)),
            'evaluated': int(np.count_nonzero(evaluated))}


def illegal_transition_rate(stages, allowed_transitions=None, reset_mask=None,
                            mask=None, reset_transitions=None):
    counts = illegal_transition_counts(stages, allowed_transitions, reset_mask,
                                       mask, reset_transitions)
    return counts['illegal'] / counts['evaluated'] if counts['evaluated'] else 0.0
