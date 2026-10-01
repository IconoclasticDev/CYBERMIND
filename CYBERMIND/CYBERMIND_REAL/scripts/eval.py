#!/usr/bin/env python3
"""Leakage-safe one- or K-step evaluation of a trained world model."""
from pathlib import Path
import argparse
import json
import sys

import numpy as np
import torch
from sklearn.metrics import f1_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.models.world_model import WorldModel
from cybermind.evaluation.metrics import binary_metrics, illegal_transition_counts
from cybermind.utils.config import load_config, edge_model_kwargs, stage_model_kwargs
from cybermind.utils.inference import verify_inference_states
from cybermind.evaluation.edge_attention import EdgeAttentionDiagnostic


def _stage_metrics(targets, predictions):
    target = np.asarray(targets, dtype=int)
    predicted = np.asarray(predictions, dtype=int)
    return {
        'accuracy': float(np.mean(target == predicted)) if len(target) else None,
        'macro_f1': float(f1_score(target, predicted, average='macro', zero_division=0)) if len(target) else None,
        'samples': int(len(target)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--split', default='test', choices=['val', 'test'])
    parser.add_argument('--threshold', type=float, default=.5)
    parser.add_argument('--horizon', type=int, default=0,
                        help='Unseen windows to score; 0 uses eval.rollout_steps')
    parser.add_argument('--explain', action='store_true',
                        help='Compute expensive per-sample explanations')
    parser.add_argument('--output', help='Report path; defaults to results/eval_SPLIT_kH.json')
    parser.add_argument('--attention-bytes-threshold', type=float, default=1048576)
    args = parser.parse_args()
    cfg = load_config(args.config)
    horizon = args.horizon or int(cfg.get('eval', {}).get('rollout_steps', 1))
    if horizon < 1:
        raise ValueError('horizon must be positive')

    root = Path(__file__).resolve().parents[1]
    dataset = GraphSequenceDataset(root / cfg['data']['processed_dir'] / f'{args.split}.pt')
    checkpoint = torch.load(root / args.checkpoint, map_location='cpu', weights_only=False)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model_cfg = cfg['model']
    model = WorldModel(
        checkpoint['node_dim'], graph_hidden=model_cfg['graph_hidden'],
        graph_out=model_cfg['graph_out'], temporal_dim=model_cfg['temporal_dim'],
        nhead=model_cfg['nhead'], temporal_layers=model_cfg['temporal_layers'],
        num_stages=model_cfg['num_stages'], dropout=model_cfg['dropout'],
        graph_heads=model_cfg.get('graph_heads', 8),
        **edge_model_kwargs(model_cfg, checkpoint['config']['model']),
        **stage_model_kwargs(cfg, checkpoint['config']),
    ).to(device)
    model.load_state_dict(checkpoint['model_state'])
    model.eval()

    risk_targets = [[] for _ in range(horizon)]
    risk_scores = [[] for _ in range(horizon)]
    stage_targets = [[] for _ in range(horizon)]
    stage_predictions = [[] for _ in range(horizon)]
    per_sample = []
    transition_totals = {'illegal': 0, 'evaluated': 0}
    attention = EdgeAttentionDiagnostic(model, checkpoint.get('normalization'),
                                        args.attention_bytes_threshold)
    from cybermind.models.stage_decoder import StageDecoder
    decoder_policy = model.stage_decoder if model.use_crf_stage else StageDecoder(model_cfg['num_stages'])
    policy = {'allowed_transitions': decoder_policy.allowed_transitions,
              'reset_transitions': decoder_policy.reset_transitions}

    for sample in dataset:
        if len(sample.states) <= horizon:
            raise ValueError(f'{sample.scenario_id}: sequence length must exceed horizon {horizon}')
        states = sample.states
        verify_inference_states(checkpoint, states)
        for state in states:
            state.x = state.x.to(device)
            state.edge_index = state.edge_index.to(device)
            state.edge_attr = state.edge_attr.to(device)
        observed, targets = states[:-horizon], states[-horizon:]
        attention.observe(observed)
        with torch.no_grad():
            forecast = model.forecast(
                observed, horizon, n_rollouts=cfg['eval'].get('n_rollouts', 16),
                seed=cfg['eval'].get('rollout_seed', 0), explain=args.explain)
        transition_counts = illegal_transition_counts(
            forecast['decoded_stages'], reset_mask=forecast['stage_reset_mask'], **policy)
        for name in transition_totals:
            transition_totals[name] += transition_counts[name]

        rows = []
        for index, target in enumerate(targets, start=1):
            probability = float(forecast['infiltration_probability'][index].item())
            predicted_stage = int(forecast['decoded_stages'][index].item())
            true_risk = int(target.y_infiltration > 0)
            true_stage = int(target.y_stage)
            risk_targets[index - 1].append(true_risk)
            risk_scores[index - 1].append(probability)
            stage_targets[index - 1].append(true_stage)
            stage_predictions[index - 1].append(predicted_stage)
            rows.append({
                'step': index, 'target_timestamp': float(target.timestamp),
                'target': true_risk, 'predicted_future_risk': probability,
                'predictive_variance': float(forecast['infiltration_variance'][index].item()),
                'target_stage': true_stage, 'predicted_stage': predicted_stage,
            })
        record = {
            'scenario': sample.scenario_id, 'observed_windows': len(observed),
            'forecast': rows, 'decoded_stages': forecast['decoded_stages'].cpu().tolist(),
            'stage_decoding': forecast['stage_decoding'],
            'stage_transition_counts': transition_counts,
        }
        if args.explain:
            record['explanation'] = forecast['explanation']
        per_sample.append(record)

    per_horizon = [{
        'step': step + 1,
        'infiltration': binary_metrics(risk_targets[step], risk_scores[step], args.threshold),
        'stage': _stage_metrics(stage_targets[step], stage_predictions[step]),
    } for step in range(horizon)]
    pooled_risk_targets = [value for row in risk_targets for value in row]
    pooled_risk_scores = [value for row in risk_scores for value in row]
    pooled_stage_targets = [value for row in stage_targets for value in row]
    pooled_stage_predictions = [value for row in stage_predictions for value in row]
    metrics = binary_metrics(pooled_risk_targets, pooled_risk_scores, args.threshold)
    stage_summary = _stage_metrics(pooled_stage_targets, pooled_stage_predictions)
    metrics['stage_accuracy'] = stage_summary['accuracy']
    metrics['stage_macro_f1'] = stage_summary['macro_f1']
    metrics['illegal_transition_rate'] = (
        transition_totals['illegal'] / transition_totals['evaluated']
        if transition_totals['evaluated'] else 0.0)
    metrics['stage_transition_pairs'] = transition_totals['evaluated']
    diagnostic = attention.report()
    metrics['mean_suspicious_edge_attention'] = diagnostic['mean_attention']
    result = {
        'split': args.split, 'forecast_horizon_windows': horizon,
        'protocol': 'states[:-H] observed; final H windows unseen and scored in order',
        'threshold': args.threshold, 'metrics': metrics, 'per_horizon': per_horizon,
        'per_sample': per_sample, 'edge_attention_diagnostic': diagnostic,
    }
    output = (root / args.output if args.output else
              root / 'results' / f'eval_{args.split}_k{horizon}.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
