#!/usr/bin/env python3
"""Evaluate the selected synthetic checkpoint on checkpoint-normalized real data."""
from collections import Counter
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.data.normalization import FeatureNormalizer
from cybermind.models.world_model import WorldModel
from cybermind.utils.config import edge_model_kwargs, stage_model_kwargs

SOURCE_QUALIFIER = 'source: zero-shot, synthetic-trained weights, real-corpus chunk — out-of-distribution test'


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def build_model(checkpoint, device):
    cfg = checkpoint['config']
    options = {key: cfg['model'][key] for key in (
        'graph_hidden', 'graph_out', 'temporal_dim', 'nhead',
        'temporal_layers', 'num_stages', 'dropout')}
    options['graph_heads'] = cfg['model'].get('graph_heads', 8)
    model = WorldModel(
        checkpoint['node_dim'], **options,
        **edge_model_kwargs(cfg['model']), **stage_model_kwargs(cfg)
    ).to(device).eval()
    model.load_state_dict(checkpoint['model_state'])
    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--processed', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args()
    torch.set_num_threads(4)
    checkpoint_path = ROOT / args.checkpoint
    processed = ROOT / args.processed
    output = ROOT / args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
    cfg = checkpoint['config']
    metadata = json.loads((processed / 'metadata.json').read_text(encoding='utf-8'))
    normalizer = FeatureNormalizer(checkpoint['normalization'])
    processed_normalizer = FeatureNormalizer.load(processed / 'normalization.json')
    dataset = GraphSequenceDataset(processed / 'test.pt')
    if not dataset.samples:
        raise ValueError('R3 held-out dataset is empty')
    first = dataset.samples[0].states[0]
    contract = {
        'checkpoint_node_dim': checkpoint['node_dim'],
        'observed_node_dim': int(first.x.shape[1]),
        'checkpoint_edge_dim': cfg['model']['edge_attr_dim'],
        'observed_edge_dim': int(first.edge_attr.shape[1]),
        'checkpoint_window_seconds': cfg['data']['window_seconds'],
        'prepared_window_seconds': dataset.samples[0].window_seconds,
        'checkpoint_history': cfg['data']['history'],
        'observed_history': len(dataset.samples[0].states),
        'checkpoint_normalization_fingerprint': normalizer.fingerprint,
        'prepared_normalization_fingerprint': processed_normalizer.fingerprint,
        'metadata_normalization_fingerprint': metadata['normalization_fingerprint'],
        'purpose': metadata['purpose'],
    }
    contract['passed'] = (
        contract['checkpoint_node_dim'] == contract['observed_node_dim'] and
        contract['checkpoint_edge_dim'] == contract['observed_edge_dim'] and
        contract['checkpoint_window_seconds'] == contract['prepared_window_seconds'] and
        contract['checkpoint_history'] == contract['observed_history'] and
        contract['checkpoint_normalization_fingerprint'] == contract['prepared_normalization_fingerprint'] ==
        contract['metadata_normalization_fingerprint'] and contract['purpose'] == 'heldout'
    )
    if not contract['passed']:
        raise ValueError(f'Checkpoint preprocessing contract mismatch: {contract}')

    model = build_model(checkpoint, args.device)
    allowed = model.stage_decoder.allowed_transitions.cpu()
    per_step = [{
        'decoded': Counter(), 'raw_argmax': Counter(), 'unknown': 0,
        'illegal': 0, 'risk_sum': 0.0, 'confidence_sum': 0.0,
        'variance_sum': 0.0,
    } for _ in range(4)]
    rows_path = output / 'per_window_predictions.jsonl.gz'
    rollouts = cfg['eval'].get('n_rollouts', 4)
    generator = torch.Generator(device=args.device).manual_seed(cfg['eval'].get('rollout_seed', 0))
    embedding_cache = {}
    batch_size = 64
    with gzip.open(rows_path, 'wt', encoding='utf-8', newline='\n') as handle, torch.no_grad():
        for offset in range(0, len(dataset), batch_size):
            samples = dataset.samples[offset:offset + batch_size]
            graph_sequences = []
            for sample in samples:
                embeddings = []
                for state in sample.states:
                    key = (state.scenario_id, state.metadata['window_start'])
                    if key not in embedding_cache:
                        state.x = state.x.to(args.device)
                        state.edge_index = state.edge_index.to(args.device)
                        state.edge_attr = state.edge_attr.to(args.device)
                        embedding_cache[key] = model.encode_state(state).detach()
                    embeddings.append(embedding_cache[key])
                graph_sequences.append(torch.stack(embeddings))
            graph_batch = torch.stack(graph_sequences)
            temporal = model.temporal(graph_batch)
            z0 = model.to_latent(temporal)[:, -1]
            expanded = z0[:, None, :].expand(len(samples), rollouts, z0.shape[-1]).reshape(-1, z0.shape[-1])
            latent = model.dynamics.rollout(expanded, 4, generator=generator)
            latent = latent.reshape(5, len(samples), rollouts, z0.shape[-1])
            risk_samples = model.infiltration_head(latent).float().sigmoid()
            risk = risk_samples.mean(dim=2).cpu()
            variance = risk_samples.var(dim=2, unbiased=False).cpu()
            emission_samples = model.stage_head(latent).float()
            probabilities = emission_samples.softmax(dim=-1).mean(dim=2)
            emissions = emission_samples.mean(dim=2)
            decoded_batch = model.decode_stages(emissions.permute(1, 0, 2)).cpu()
            raw_batch = probabilities.argmax(dim=-1).permute(1, 0).cpu()
            probabilities = probabilities.permute(1, 0, 2).cpu()
            for local_index, sample in enumerate(samples):
                index = offset + local_index
                decoded = decoded_batch[local_index].tolist()
                raw = raw_batch[local_index].tolist()
                predictions = []
                for step in range(1, 5):
                    illegal = not bool(allowed[decoded[step - 1], decoded[step]])
                    confidence = float(probabilities[local_index, step].max())
                    entry = {
                        'step': step,
                        'decoded_stage': int(decoded[step]),
                        'raw_argmax_stage': int(raw[step]),
                        'stage_confidence': confidence,
                        'stage_probabilities': probabilities[local_index, step].tolist(),
                        'infiltration_probability': float(risk[step, local_index]),
                        'infiltration_variance': float(variance[step, local_index]),
                        'illegal_incoming_transition': illegal,
                    }
                    predictions.append(entry)
                    aggregate = per_step[step - 1]
                    aggregate['decoded'][int(decoded[step])] += 1
                    aggregate['raw_argmax'][int(raw[step])] += 1
                    aggregate['unknown'] += int(decoded[step] == 6)
                    aggregate['illegal'] += int(illegal)
                    aggregate['risk_sum'] += float(risk[step, local_index])
                    aggregate['confidence_sum'] += confidence
                    aggregate['variance_sum'] += float(variance[step, local_index])
                row = {
                    'source_qualifier': SOURCE_QUALIFIER,
                    'sample_index': index,
                    'scenario_id': sample.scenario_id,
                    'observed_window_starts': [state.metadata['window_start'] for state in sample.states],
                    'observed_target_stages': [int(state.y_stage) for state in sample.states],
                    'predictions': predictions,
                }
                handle.write(json.dumps(row, separators=(',', ':')) + '\n')

    count = len(dataset)
    summary_steps = []
    for index, values in enumerate(per_step, start=1):
        summary_steps.append({
            'step': index,
            'samples': count,
            'decoded_stage_histogram': {str(key): value for key, value in sorted(values['decoded'].items())},
            'raw_argmax_stage_histogram': {str(key): value for key, value in sorted(values['raw_argmax'].items())},
            'distinct_non_unknown_stages': len(set(values['decoded']) - {6}),
            'unknown_count': values['unknown'],
            'illegal_transition_count': values['illegal'],
            'illegal_transition_rate': values['illegal'] / count,
            'mean_infiltration_probability': values['risk_sum'] / count,
            'mean_stage_confidence': values['confidence_sum'] / count,
            'mean_infiltration_variance': values['variance_sum'] / count,
        })
    report = {
        'source_qualifier': SOURCE_QUALIFIER,
        'checkpoint': str(checkpoint_path),
        'checkpoint_sha256': sha256(checkpoint_path),
        'selected_epoch': checkpoint['epoch'],
        'device': args.device,
        'samples': count,
        'preprocessing_contract': contract,
        'stage_reset_mask_declared': False,
        'rollout_steps': 4,
        'n_rollouts': rollouts,
        'inference_batch_size': batch_size,
        'rollout_seed': cfg['eval'].get('rollout_seed', 0),
        'per_step': summary_steps,
        'predictions_path': str(rows_path),
        'predictions_sha256': sha256(rows_path),
        'lateral_movement_disclosure': 'Real-chunk validation does not include a Lateral Movement transition. Kill-chain-diversity validation on real data covers the other represented stages only; it does not validate Lateral Movement.',
        'fallback_feature_disclosure': "flow_feature_source: CYBERMIND custom directional packet exporter; 40-column schema; satisfies the project's 20-field packet-feature contract when verified, but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter traffic-statistic columns. No CICFlowMeter feature parity is claimed.",
    }
    report_path = output / 'summary.json'
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'predictions_path'}, indent=2))


if __name__ == '__main__':
    main()
