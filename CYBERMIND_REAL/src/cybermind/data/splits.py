from __future__ import annotations
from collections import defaultdict
from typing import Iterable
import hashlib


def stable_bucket(key: str) -> float:
    h=hashlib.sha256(key.encode()).hexdigest()[:12]
    return int(h,16)/float(16**12)


def group_split(items, key_fn, train=.70, val=.15):
    """Deterministic group/scenario split; no row leakage."""
    groups=sorted(set(key_fn(x) for x in items), key=lambda x:(stable_bucket(str(x)),str(x)))
    if len(groups)<3:
        return {'train':groups[:max(1,len(groups)-2)],'val':groups[-2:-1],'test':groups[-1:]}
    n=len(groups); ntr=max(1,int(n*train)); nv=max(1,int(n*val))
    return {'train':groups[:ntr],'val':groups[ntr:ntr+nv],'test':groups[ntr+nv:]}


def unseen_attack_split(samples, attack_key='attack_family'):
    """Leave an entire attack family/scenario out of test. Uses metadata when available."""
    families=[]
    for s in samples:
        fam=s.metadata.get(attack_key) or s.metadata.get('scenario_id') or s.scenario_id
        families.append(str(fam))
    uniq=sorted(set(families))
    held=uniq[-1:] if uniq else []
    return held
