"""CPU inference and auditable, label-free analyst presentation helpers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import torch
from cybermind.counterfactual.simulator import Intervention, mutate_state
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.models.world_model import WorldModel
from cybermind.models.stage_decoder import StageDecoder
from cybermind.utils.config import edge_model_kwargs, stage_model_kwargs
from cybermind.utils.inference import verify_inference_states

STAGES = ('Benign', 'Reconnaissance', 'Initial Access', 'Lateral Movement',
          'Command & Control', 'Exfiltration', 'Unknown/Ambiguous')
CLAIM = 'passes under the reviewed protocol on synthetic verification data'


def stage_name(value):
    return STAGES[value] if 0 <= value < len(STAGES) else f'Unmapped ({value})'


def load_case(checkpoint_path, root, index=0):
    path = Path(checkpoint_path)
    ck = torch.load(path, map_location='cpu', weights_only=False)
    cfg = ck['config']; mc = cfg['model']
    model = WorldModel(ck['node_dim'], **{key: mc[key] for key in
        ('graph_hidden', 'graph_out', 'temporal_dim', 'nhead', 'temporal_layers',
         'num_stages', 'dropout')}, graph_heads=mc.get('graph_heads', 8),
         **edge_model_kwargs(mc), **stage_model_kwargs(cfg))
    model.load_state_dict(ck['model_state']); model.eval()
    data_path = Path(root) / cfg['data']['processed_dir'] / 'test.pt'
    ds = GraphSequenceDataset(data_path)
    if not len(ds):
        raise ValueError('test.pt is empty')
    sample = ds[index]
    if len(sample.states) < 2:
        raise ValueError('At least two states are required to hold out the target')
    verify_inference_states(ck, sample.states)
    lineage = {'checkpoint': str(path.resolve()),
               'checkpoint_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'checkpoint_epoch': ck.get('epoch'), 'dataset': str(data_path.resolve()),
               'dataset_sha256': hashlib.sha256(data_path.read_bytes()).hexdigest(),
               'split': 'test', 'sequence_index': index, 'scenario': sample.scenario_id,
               'source': sample.metadata.get('source', 'unavailable'),
               'selection_metric': cfg['train'].get('selection_metric', 'val_f1'),
               'selection_f1_tolerance': cfg['train'].get('selection_f1_tolerance'),
               'normalization': sample.states[-2].metadata.get('normalization_fingerprint', 'unavailable')}
    return model, cfg, sample, lineage, len(ds)


def forecast_rows(out, model, timestamp, window_seconds):
    probabilities = out['infiltration_probability'].detach().cpu()
    variances = out['infiltration_variance'].detach().cpu()
    stages = out['decoded_stages'].detach().cpu().tolist()
    policy = model.stage_decoder if model.use_crf_stage else StageDecoder(len(STAGES))
    allowed = policy.allowed_transitions.cpu(); resets = policy.reset_transitions.cpu()
    reset_mask = out['stage_reset_mask'].cpu()
    rows = []
    for step, stage in enumerate(stages):
        legal = None if step == 0 else bool(allowed[stages[step-1], stage] or
                     (reset_mask[step] and resets[stages[step-1], stage]))
        rows.append({'step': step, 'horizon': 'Now (encoded)' if step == 0 else f'+{step}',
                     'timestamp': float(timestamp + step * window_seconds),
                     'risk': float(probabilities[step]),
                     'rollout_std': float(variances[step].sqrt()),
                     'stage': stage_name(stage), 'stage_id': stage,
                     'transition_legal': legal, 'declared_reset': bool(reset_mask[step])})
    return rows


def network_dot(state, effects=None, limit=80):
    """Bounded topology, with untrusted host identifiers safely quoted."""
    effects = effects or {}
    lines = ['digraph network {', 'rankdir=LR;']
    for index, name in enumerate(state.node_ids[:limit]):
        effect = effects.get(index)
        label = str(name) + (f'\nmodel risk reduction {effect:+.3f}' if effect is not None else '')
        color = '#f5c16c' if effect is not None and effect > 0 else '#a7c7e7'
        lines.append(f'{index} [label={json.dumps(label)}, style=filled, fillcolor="{color}"];')
    for source, target in state.edge_index.cpu().t().tolist():
        if source < limit and target < limit:
            lines.append(f'{source} -> {target};')
    return '\n'.join(lines + ['}'])


def compare_isolations(model, states, hosts, k, n_rollouts, seed):
    """Retain history and common random draws; mutate only the final observed graph.

    Existing simulator operations act in model feature space, so these are
    sensitivity probes, never promised physical containment effects.
    """
    with torch.no_grad():
        baseline = float(model.forecast(states, k, n_rollouts=n_rollouts, seed=seed,
                                       explain=False)['infiltration_probability'][-1])
        rows = [{'action': 'No Action', 'host_index': None, 'host': None,
                 'future_risk': baseline, 'risk_reduction': 0.0}]
        for host in hosts:
            if not 0 <= host < len(states[-1].node_ids):
                raise ValueError('Host index is out of range')
            altered = list(states[:-1]) + [mutate_state(states[-1], Intervention('Isolate Host', host=host))]
            risk = float(model.forecast(altered, k, n_rollouts=n_rollouts, seed=seed,
                                       explain=False)['infiltration_probability'][-1])
            rows.append({'action': 'Simulate isolation', 'host_index': host,
                         'host': states[-1].node_ids[host], 'future_risk': risk,
                         'risk_reduction': baseline-risk})
    return sorted(rows, key=lambda row: row['future_risk'])
