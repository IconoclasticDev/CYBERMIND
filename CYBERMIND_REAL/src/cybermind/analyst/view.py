"""CPU inference and auditable, label-free analyst presentation helpers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pandas as pd
import torch
from cybermind.counterfactual.simulator import Intervention, mutate_state
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.data.graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
from cybermind.data.adapters.unified import UnifiedAdapter
from cybermind.data.normalization import FeatureNormalizer
from cybermind.data.pcap_extract import PACKET_FEATURES, pcap_to_dataframe
from cybermind.data.temporal import make_sequences
from cybermind.models.world_model import WorldModel
from cybermind.models.stage_decoder import StageDecoder
from cybermind.utils.config import edge_model_kwargs, stage_model_kwargs
from cybermind.utils.inference import verify_inference_states

STAGES = ('Benign', 'Reconnaissance', 'Initial Access', 'Lateral Movement',
          'Command & Control', 'Exfiltration', 'Unknown/Ambiguous')
CLAIM = 'passes under the reviewed protocol on synthetic verification data'


def stage_name(value):
    return STAGES[value] if 0 <= value < len(STAGES) else f'Unmapped ({value})'


def load_checkpoint(checkpoint_path):
    path = Path(checkpoint_path)
    ck = torch.load(path, map_location='cpu', weights_only=False)
    cfg = ck['config']; mc = cfg['model']
    from cybermind.models.graph_encoder import HAS_PYG, PYG_IMPORT_ERROR
    if not HAS_PYG and 'graph.conv1.lin_l.weight' in ck['model_state']:
        raise RuntimeError(f'This checkpoint requires PyTorch Geometric GATv2Conv; import failed: {PYG_IMPORT_ERROR}')
    model = WorldModel(ck['node_dim'], **{key: mc[key] for key in
        ('graph_hidden', 'graph_out', 'temporal_dim', 'nhead', 'temporal_layers',
         'num_stages', 'dropout')}, graph_heads=mc.get('graph_heads', 8),
         **edge_model_kwargs(mc), **stage_model_kwargs(cfg))
    model.load_state_dict(ck['model_state']); model.eval()
    return model, ck, cfg


def load_case(checkpoint_path, root, index=0):
    path = Path(checkpoint_path)
    model, ck, cfg = load_checkpoint(path)
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


def load_uploaded_session(checkpoint_path, input_path):
    """Parse one unlabeled capture into every replayable observed history."""
    path = Path(input_path)
    model, checkpoint, cfg = load_checkpoint(checkpoint_path)
    suffix = path.suffix.lower()
    if suffix in ('.pcap', '.pcapng'):
        frame = pcap_to_dataframe(path, label=None)
        input_format = 'PCAP'
    elif suffix == '.csv':
        frame, _ = UnifiedAdapter('USER_UPLOAD').convert(path)
        input_format = 'CSV'
    else:
        raise ValueError('Input must be .pcap, .pcapng, or .csv')
    if frame.empty:
        raise ValueError('Input contains no usable IPv4 flow records')
    frame = frame.copy()
    frame['timestamp'] = pd.to_datetime(frame['timestamp'], errors='coerce', utc=True)
    if frame.timestamp.isna().any():
        raise ValueError('Every uploaded row needs a valid timestamp')
    if frame.src.fillna('').astype(str).str.strip().eq('').any() or frame.dst.fillna('').astype(str).str.strip().eq('').any():
        raise ValueError('Every uploaded row needs source and destination endpoint identities')
    frame['label'] = 'UNLABELED'
    frame['infiltration'] = 0.0
    frame['stage'] = len(STAGES) - 1
    frame['source'] = 'USER_UPLOAD'
    coverage = float(frame.get('packet_features_available', 0.0).mean()
                     if hasattr(frame.get('packet_features_available', 0.0), 'mean') else 0.0)
    if cfg['data'].get('require_packet_features', False) and coverage < 1.0:
        missing = [name for name in PACKET_FEATURES if name not in frame]
        raise ValueError('This checkpoint requires complete packet telemetry; '
                         f'the upload has coverage {coverage:.1%} and is missing {missing}')
    constants = checkpoint.get('normalization')
    if cfg['data'].get('require_normalization', False) and constants is None:
        raise ValueError('Checkpoint does not contain its required training normalization')
    normalizer = FeatureNormalizer(constants) if constants else None
    metadata = {'source': 'USER_UPLOAD', 'input_format': input_format,
                'source_files': [path.name], 'split': 'inference',
                'endpoint_method': 'columns', 'stage_method': 'unlabeled_inference',
                'packet_feature_coverage': coverage}
    sequences = make_sequences(
        frame, f'upload::{path.name}', window_seconds=cfg['data']['window_seconds'],
        history=cfg['data']['history'], stride_seconds=cfg['data']['stride_seconds'],
        metadata=metadata, normalizer=normalizer)
    if not sequences:
        duration = (frame.timestamp.max() - frame.timestamp.min()).total_seconds()
        raise ValueError(f'Input spans {duration:.1f}s and does not provide the configured '
                         f'{cfg["data"]["history"]}-window history')
    lineage = {
        'checkpoint': str(Path(checkpoint_path).resolve()),
        'checkpoint_sha256': hashlib.sha256(Path(checkpoint_path).read_bytes()).hexdigest(),
        'checkpoint_epoch': checkpoint.get('epoch'), 'dataset': str(path.resolve()),
        'dataset_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'split': 'live_upload_unlabeled',
        'scenario': sequences[-1].scenario_id, 'source': 'USER_UPLOAD',
        'input_format': input_format, 'packet_feature_coverage': coverage,
        'normalization': sequences[-1].states[-1].metadata.get('normalization_fingerprint', 'unavailable'),
    }
    return model, cfg, sequences, lineage, frame


def select_uploaded_sequence(session, index=-1):
    """Select an observed history without reparsing the capture or using future labels."""
    model, cfg, sequences, base_lineage, frame = session
    if not -len(sequences) <= index < len(sequences):
        raise IndexError('Replay window is out of range')
    position = index % len(sequences)
    sample = sequences[position]
    sample.metadata = dict(sample.metadata)
    sample.metadata['observed_flow_rows'] = observed_flow_rows(frame, sample.states[-1])
    lineage = {**base_lineage, 'sequence_index': position}
    return model, cfg, sample, lineage, len(sequences)


def load_uploaded_case(checkpoint_path, input_path):
    """Compatibility helper: load the latest replayable history from a capture."""
    return select_uploaded_sequence(load_uploaded_session(checkpoint_path, input_path))

def observed_flow_rows(frame, state, limit=200):
    """Bounded source telemetry from the final observed window, not model scores."""
    start = state.metadata['window_start']
    end = state.metadata['window_end']
    epoch = pd.to_datetime(frame['timestamp'], utc=True).astype('datetime64[ns, UTC]').astype('int64') / 1e9
    observed = frame.loc[(epoch >= start) & (epoch < end)].copy()
    if observed.empty:
        return []
    signals = []
    for row in observed.itertuples(index=False):
        reasons = []
        if float(getattr(row, 'scan_unique_ports', 0) or 0) >= 4:
            if float(getattr(row, 'scan_sequential_score', 0) or 0) >= 0.5:
                reasons.append('sequential port access')
            if float(getattr(row, 'scan_randomized_score', 0) or 0) >= 0.5:
                reasons.append('irregular port access')
        if float(getattr(row, 'retransmission_count', 0) or 0) > 0:
            reasons.append('TCP retransmissions')
        signals.append(', '.join(reasons))
    observed['review_signal'] = signals
    observed['review_flag'] = observed['review_signal'].ne('')
    observed = observed.sort_values(['review_flag', 'timestamp'], ascending=[False, False], kind='stable')
    columns = ('timestamp', 'src', 'src_port', 'dst', 'dst_port', 'protocol',
               'bytes_fwd', 'packets_fwd', 'review_flag', 'review_signal')
    return observed.loc[:, [column for column in columns if column in observed]].head(limit).to_dict('records')


def input_shift_summary(states, threshold=6.0):
    """Heuristic tail check on training-normalized features, not a calibrated OOD score."""
    if not states:
        return {'available': False, 'reason': 'No observed states'}
    if any(state.metadata.get('normalization_fingerprint') in (None, 'unavailable')
           for state in states):
        return {'available': False, 'reason': 'Training normalization is unavailable'}
    counters = {}
    total, exceeded = 0, 0
    for state in states:
        for kind, values, names in (
            ('node', state.x, NODE_FEATURE_NAMES),
            ('edge', state.edge_attr, EDGE_FEATURE_NAMES),
        ):
            if values.numel() == 0:
                continue
            over = (values.detach().abs().cpu() > threshold)
            total += over.numel()
            exceeded += int(over.sum())
            for column, count in enumerate(over.sum(dim=0).tolist()):
                if count:
                    key = f'{kind}.{names[column]}'
                    counters[key] = counters.get(key, 0) + count
    return {'available': True, 'threshold_std': threshold,
            'exceeded_values': exceeded, 'total_values': total,
            'fraction': exceeded / total if total else 0.0,
            'top_features': [{'feature': name, 'exceedances': count}
                             for name, count in sorted(counters.items(), key=lambda item: (-item[1], item[0]))[:5]],
            'limitation': 'Heuristic feature-range cue only; not a calibrated OOD detector or reliability guarantee.'}

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
