#!/usr/bin/env python3
"""CPU-only, same-split comparison with explicit input and target contracts."""
from pathlib import Path
import argparse
import json
import sys
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.baselines.protocol import evaluate_baseline, metric_report, sample_target, sha256
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.models.world_model import WorldModel
from cybermind.utils.config import edge_model_kwargs, stage_model_kwargs
from cybermind.utils.inference import verify_inference_states


def compare(checkpoint, split='test', threshold=0.5):
    checkpoint = Path(checkpoint)
    ck = torch.load(checkpoint, map_location='cpu', weights_only=False)
    cfg = ck['config']
    processed = ROOT / cfg['data']['processed_dir']
    mc = cfg['model']
    model = WorldModel(ck['node_dim'], **{key: mc[key] for key in (
        'graph_hidden', 'graph_out', 'temporal_dim', 'nhead', 'temporal_layers', 'num_stages', 'dropout')},
        graph_heads=mc.get('graph_heads', 8), **edge_model_kwargs(mc, mc),
        **stage_model_kwargs(cfg, cfg))
    model.load_state_dict(ck['model_state'])
    model.eval()
    rows = []
    for mode in ('node', 'node_edge'):
        rows.append(evaluate_baseline(processed, split, mode, threshold))
    if mc.get('periodic_clock') is not None:
        rows.append(evaluate_baseline(processed, split, 'node_edge', threshold, mc['periodic_clock']))
    ds = GraphSequenceDataset(processed / f'{split}.pt')
    probabilities = []
    for sample in ds:
        verify_inference_states(ck, sample.states)
        with torch.no_grad():
            result = model.forecast(sample.states[:-1], 1,
                                   n_rollouts=cfg['eval'].get('n_rollouts', 16),
                                   seed=cfg['eval'].get('rollout_seed', 0))
        probabilities.append(float(result['infiltration_probability'][-1]))
    targets = [sample_target(sample) for sample in ds]
    metrics, counts = metric_report(targets, probabilities, threshold)
    for row in rows:
        if [item['target'] for item in row['per_sample']] != targets:
            raise ValueError('Comparison targets or sample order differ')
    world = {
        'model': 'world_model', 'selected_epoch': ck.get('epoch'),
        'checkpoint_sha256': sha256(checkpoint), 'metrics': metrics, 'confusion_counts': counts,
        'per_sample': [{'scenario': sample.scenario_id, 'target_timestamp': float(sample.states[-1].timestamp),
                        'target': target, 'predicted_future_risk': probability}
                       for sample, target, probability in zip(ds, targets, probabilities)],
        'features': {'node_columns': ck['node_dim'],
                     'edge_columns': int(ds[0].states[0].edge_attr.shape[1]) if mc.get('use_edge_features', False) and len(ds) else 0,
                     'periodic_clock': mc.get('periodic_clock'), 'graph_topology': True},
    }
    for row in rows:
        registry = row['feature_registry']
        row['feature_coverage_matches_world_model'] = (
            registry['node_columns'] == world['features']['node_columns'] and
            registry['edge_columns'] == world['features']['edge_columns'] and
            registry['periodic_clock'] == world['features']['periodic_clock'])
    return {
        'evidence_scope': 'synthetic verification only; not a real-data benchmark',
        'device': 'cpu', 'split': split, 'threshold': threshold,
        'threshold_provenance': 'fixed command input; no test tuning',
        'forecast_horizon_windows': 1, 'sample_alignment_verified': True,
        'selection_policy': {k: cfg['train'].get(k) for k in (
            'selection_metric', 'selection_f1_tolerance', 'selection_stage_metric')},
        'baselines': rows, 'world_model': world,
        'limitations': [
            'Feature coverage parity does not equal architecture parity: pooled baseline discards graph topology.',
            'All models receive the same observed windows and predict the same unseen final-window infiltration label.',
            'One-step infiltration comparison does not establish four-step stage forecasting accuracy.',
            'Historical whole-sequence baseline numbers are not comparable to this corrected protocol.',
        ],
    }


def markdown(report):
    def number(value):
        return 'undefined' if value is None else f'{value:.6f}'
    lines = [
        '# Track A comparison',
        '',
        report['evidence_scope'] + '. The Phase 3 audit claim remains: "passes under the reviewed protocol on synthetic verification data." This one-step table is not a new stage-gate audit.',
        '',
        f"CPU; split {report['split']}; fixed threshold {report['threshold']}; one unseen target window.",
        '',
        '| Model | Node / edge / periodic columns | Feature coverage parity | F1 | Precision | Recall | FPR | AP | ROC-AUC |',
        '|---|---|---|---|---|---|---|---|---|',
    ]
    for row in report['baselines']:
        r, m = row['feature_registry'], row['metrics']
        lines.append('| ' + ' | '.join([
            row['baseline'], f"{r['node_columns']} / {r['edge_columns']} / {r['periodic_columns']}",
            'yes (pooling discards topology)' if row['feature_coverage_matches_world_model'] else 'no',
            *[number(m[k]) for k in ('f1', 'precision', 'recall', 'fpr', 'ap', 'roc_auc')]]) + ' |')
    w = report['world_model']
    f = w['features']
    lines.append('| ' + ' | '.join([
        f"World model, selected epoch {w['selected_epoch']}",
        f"{f['node_columns']} / {f['edge_columns']} / {2 if f['periodic_clock'] else 0}", 'reference',
        *[number(w['metrics'][k]) for k in ('f1', 'precision', 'recall', 'fpr', 'ap', 'roc_auc')]]) + ' |')
    lines.extend(['', *['- ' + item for item in report['limitations']], '',
                  'FPR = FP / (FP + TN); undefined when the split has no negative examples. Full counts, probabilities, input hashes, feature registry hashes and protocol hash are retained in comparison.json.', ''])
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint', required=True)
    p.add_argument('--split', choices=['val', 'test'], default='test')
    p.add_argument('--threshold', type=float, default=0.5)
    p.add_argument('--output-dir', required=True)
    args = p.parse_args()
    torch.set_num_threads(2)
    output = ROOT / args.output_dir
    if (output / 'comparison.json').exists():
        raise FileExistsError('Use a new output directory to preserve prior comparison evidence')
    report = compare(ROOT / args.checkpoint, args.split, args.threshold)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'comparison.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    (output / 'comparison.md').write_text(markdown(report), encoding='utf-8')
    print(markdown(report))


if __name__ == '__main__':
    main()
