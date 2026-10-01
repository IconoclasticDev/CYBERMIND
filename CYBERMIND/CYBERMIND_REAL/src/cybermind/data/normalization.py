"""Persisted training-only fp32 graph feature normalization.

Fit once on unique training windows. Validation, test, and inference only transform.
Feature names are checked so legacy checkpoints cannot silently consume a new schema.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import torch


class RunningMoments:
    def __init__(self, width):
        self.count = 0
        self.mean = torch.zeros(width, dtype=torch.float32)
        self.m2 = torch.zeros(width, dtype=torch.float32)

    def update(self, values):
        x = torch.as_tensor(values, dtype=torch.float32).detach().cpu()
        if x.ndim != 2 or x.shape[1] != self.mean.numel():
            raise ValueError('Feature width does not match normalization schema')
        if not torch.isfinite(x).all():
            raise ValueError('Cannot fit normalization to non-finite features')
        if not len(x):
            return
        n = len(x)
        mean = x.mean(0)
        m2 = ((x - mean) ** 2).sum(0)
        delta = mean - self.mean
        total = self.count + n
        self.m2 += m2 + delta.square() * (self.count * n / total)
        self.mean += delta * (n / total)
        self.count = total

    def constants(self):
        std = (self.m2 / max(self.count, 1)).clamp_min(0).sqrt()
        std = torch.where(std > 1e-6, std, torch.ones_like(std))
        if not torch.isfinite(self.mean).all() or not torch.isfinite(std).all():
            raise ValueError('fp32 normalization overflow: inspect extreme input features')
        return {'count': self.count, 'mean': self.mean.tolist(), 'std': std.tolist()}


class FeatureNormalizer:
    def __init__(self, constants):
        from .graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
        if constants.get('fit_split') != 'train' or constants.get('dtype') != 'float32':
            raise ValueError('Normalization must be fitted on training data in fp32')
        self.constants = constants
        for key, names in [('node', NODE_FEATURE_NAMES), ('edge', EDGE_FEATURE_NAMES)]:
            if constants[key]['features'] != list(names):
                raise ValueError(f'{key} normalization feature schema mismatch')
            mean = torch.tensor(constants[key]['mean'], dtype=torch.float32)
            std = torch.tensor(constants[key]['std'], dtype=torch.float32)
            if len(mean) != len(names) or len(std) != len(names) or not torch.isfinite(mean).all() or not torch.isfinite(std).all() or (std <= 0).any():
                raise ValueError(f'Invalid {key} normalization constants')

    @property
    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.constants, sort_keys=True).encode()).hexdigest()

    @classmethod
    def fit(cls, states):
        from .graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
        node, edge = RunningMoments(len(NODE_FEATURE_NAMES)), RunningMoments(len(EDGE_FEATURE_NAMES))
        seen = set()
        for state in states:
            if state.metadata.get('split') != 'train':
                raise ValueError('Only training states may fit normalization')
            if state.metadata.get('normalization_fingerprint'):
                raise ValueError('Normalization must fit raw features')
            identity = (state.scenario_id, state.metadata.get('window_start', state.timestamp))
            if identity in seen:
                continue
            seen.add(identity)
            node.update(state.x)
            edge.update(state.edge_attr)
        if not node.count:
            raise ValueError('No training nodes available for normalization')
        return cls({'version': 1, 'fit_split': 'train', 'dtype': 'float32',
                    'method': 'population_mean_std', 'training_windows': len(seen),
                    'node': {'features': list(NODE_FEATURE_NAMES), **node.constants()},
                    'edge': {'features': list(EDGE_FEATURE_NAMES), **edge.constants()}})

    def transform(self, values, kind):
        x = values.to(dtype=torch.float32)
        c = self.constants[kind]
        mean = torch.tensor(c['mean'], dtype=torch.float32, device=x.device)
        std = torch.tensor(c['std'], dtype=torch.float32, device=x.device)
        result = (x - mean) / std
        if not torch.isfinite(result).all():
            raise ValueError('Non-finite normalized features')
        return result

    def inverse_transform(self, values, kind):
        x = values.to(dtype=torch.float32)
        c = self.constants[kind]
        mean = torch.tensor(c['mean'], dtype=torch.float32, device=x.device)
        std = torch.tensor(c['std'], dtype=torch.float32, device=x.device)
        result = x * std + mean
        if not torch.isfinite(result).all():
            raise ValueError('Non-finite inverse-normalized features')
        return result

    def save(self, path):
        Path(path).write_text(json.dumps(self.constants, indent=2), encoding='utf-8')

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding='utf-8')))
