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

SOURCE_QUALIFIER = 'source: real-chunk validation, pre-Phase-5 — not full-corpus accuracy'


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
    for mode in ('node', 'node_edge', 'feature_matched'):
        rows.append(evaluate_baseline(processed, split, mode, threshold))
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
    majority_metrics, majority_counts = metric_report(targets, [0.0] * len(targets), threshold)
    for row in rows:
        if [item['target'] for item in row['per_sample']] != targets:
            raise ValueError('Comparison targets or sample order differ')
    world = {
        'source_qualifier': SOURCE_QUALIFIER,
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
        row['source_qualifier'] = SOURCE_QUALIFIER
        registry = row['feature_registry']
        row['feature_coverage_matches_world_model'] = (
            registry['feature_mode'] == 'feature_matched' and
            registry['node_columns'] == world['features']['node_columns'] and
            registry['edge_columns'] == world['features']['edge_columns'] and
            registry['periodic_clock'] == world['features']['periodic_clock'])
    matched = next(row for row in rows if row['feature_registry']['feature_mode'] == 'feature_matched')
    delta = world['metrics']['f1'] - matched['metrics']['f1']
    verdict = 'beats' if delta > 0 else 'loses to' if delta < 0 else 'ties'
    world_accuracy = (counts['tp'] + counts['tn']) / len(targets)
    majority_accuracy = (majority_counts['tp'] + majority_counts['tn']) / len(targets)
    fallback_modes = [row['feature_registry']['feature_mode'] for row in rows
                      if row['baseline'] == 'dummy_prior_single_class']
    return {
        'source_qualifier': SOURCE_QUALIFIER,
        'evidence_scope': SOURCE_QUALIFIER,
        'device': 'cpu', 'split': split, 'threshold': threshold,
        'threshold_provenance': 'fixed command input; no test tuning',
        'forecast_horizon_windows': 1, 'sample_alignment_verified': True,
        'selection_policy': {k: cfg['train'].get(k) for k in (
            'selection_metric', 'selection_f1_tolerance', 'selection_stage_metric')},
        'baselines': rows, 'world_model': world,
        'trivial_majority_baseline': {
            'source_qualifier': SOURCE_QUALIFIER,
            'baseline': 'always_benign', 'threshold': threshold,
            'metrics': majority_metrics, 'confusion_counts': majority_counts,
            'per_sample': [{'scenario': sample.scenario_id,
                            'target_timestamp': float(sample.states[-1].timestamp),
                            'target': target, 'predicted_future_risk': 0.0}
                           for sample, target in zip(ds, targets)],
        },
        'model_vs_feature_matched': {
            'primary_metric': 'f1', 'world_model_f1': world['metrics']['f1'],
            'feature_matched_f1': matched['metrics']['f1'], 'difference': delta,
            'verdict': verdict,
            'sentence': f"The model {verdict} the feature-matched baseline on real data."
        },
        'model_vs_always_benign': {
            'world_model_f1': world['metrics']['f1'],
            'always_benign_f1': majority_metrics['f1'],
            'world_model_accuracy': world_accuracy,
            'always_benign_accuracy': majority_accuracy,
            'world_model_fpr': world['metrics']['fpr'],
            'always_benign_fpr': majority_metrics['fpr'],
            'verdict': 'model better on F1 and accuracy; equal FPR',
        },
        'single_class_fallback': {
            'policy': 'If the training target has one class, emit its constant prior probability instead of fitting logistic regression.',
            'invoked': bool(fallback_modes), 'invoked_modes': fallback_modes,
            'training_target_counts': rows[0]['training_target_counts'],
        },
        'limitations': [
            'The feature-matched logistic baseline receives every node and edge column plus topology summaries, but fixed aggregation cannot reproduce the world model graph architecture or exact adjacency-message interactions.',
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
        report['evidence_scope'] + '. This label applies to every number below.',
        '',
        f"CPU; split {report['split']}; fixed threshold {report['threshold']}; one unseen target window.",
        '',
        '| Model | Node / edge / periodic columns | Feature coverage parity | TP | FP | TN | FN | F1 | Precision | Recall | FPR | AP | ROC-AUC |',
        '|---|---|---|---:|---:|---:|---:|---|---|---|---|---|---|',
    ]
    for row in report['baselines']:
        r, m = row['feature_registry'], row['metrics']
        lines.append('| ' + ' | '.join([
            f"{row['baseline']} ({r['feature_mode']})", f"{r['node_columns']} / {r['edge_columns']} / {r['periodic_columns']}",
            'yes; topology summarized' if row['feature_coverage_matches_world_model'] else 'no',
            *[str(row['confusion_counts'][k]) for k in ('tp', 'fp', 'tn', 'fn')],
            *[number(m[k]) for k in ('f1', 'precision', 'recall', 'fpr', 'ap', 'roc_auc')]]) + ' |')
    w = report['world_model']
    f = w['features']
    lines.append('| ' + ' | '.join([
        f"World model, selected epoch {w['selected_epoch']}",
        f"{f['node_columns']} / {f['edge_columns']} / {2 if f['periodic_clock'] else 0}", 'reference',
        *[str(w['confusion_counts'][k]) for k in ('tp', 'fp', 'tn', 'fn')],
        *[number(w['metrics'][k]) for k in ('f1', 'precision', 'recall', 'fpr', 'ap', 'roc_auc')]]) + ' |')
    majority = report['trivial_majority_baseline']; m = majority['metrics']
    lines.append('| ' + ' | '.join([
        'Always Benign', '0 / 0 / 0', 'trivial reference',
        *[str(majority['confusion_counts'][k]) for k in ('tp', 'fp', 'tn', 'fn')],
        *[number(m[k]) for k in ('f1', 'precision', 'recall', 'fpr', 'ap', 'roc_auc')]]) + ' |')
    lines.extend(['', f"**{report['model_vs_feature_matched']['sentence']}**", '',
                  ('Always-Benign comparison: ' + report['model_vs_always_benign']['verdict'] +
                   f" (model accuracy {report['model_vs_always_benign']['world_model_accuracy']:.6f}; "
                   f"always-Benign accuracy {report['model_vs_always_benign']['always_benign_accuracy']:.6f})."),
                  ('Single-class training fallback invoked: ' +
                   ('yes' if report['single_class_fallback']['invoked'] else 'no') +
                   f"; training targets were {report['single_class_fallback']['training_target_counts']['negative']} negative / "
                   f"{report['single_class_fallback']['training_target_counts']['positive']} positive."), '',
                  *['- ' + item for item in report['limitations']], '',
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
