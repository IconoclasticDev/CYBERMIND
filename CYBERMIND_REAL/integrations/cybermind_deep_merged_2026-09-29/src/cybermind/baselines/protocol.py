"""Shared, auditable forecasting protocol for CPU baseline comparisons."""
from pathlib import Path
import hashlib
import json
import numpy as np
from sklearn.metrics import roc_auc_score
from cybermind.baselines.logistic import LogisticBaseline
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.evaluation.metrics import binary_metrics

PROTOCOL = {
    'version': 4,
    'input': 'states[:-H], in chronological order',
    'target': 'each of the final H unseen windows',
    'forecast_horizon_windows': 'H, supplied before evaluation',
    'pooling': 'per-window arithmetic means; flatten windows in time order',
    'threshold_provenance': 'fixed in advance; never fitted on evaluation labels',
    'baseline_scaling': 'StandardScaler fitted on training split only',
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def record_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def sample_targets(sample, horizon=1):
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError('Forecast horizon must be a positive integer')
    if len(sample.states) <= horizon:
        raise ValueError('Forecasting requires observed history before all unseen target windows')
    return [int(state.y_infiltration > 0) for state in sample.states[-horizon:]]


def sample_target(sample):
    return sample_targets(sample, 1)[0]


def _topology_features(state):
    """Fixed-width summaries derived only from the observed edge_index."""
    nodes = int(state.x.shape[0]); edge_index = state.edge_index.detach().cpu().numpy()
    edges = int(edge_index.shape[1])
    if edges:
        source, destination = edge_index
        indegree = np.bincount(destination, minlength=nodes).astype(float)
        outdegree = np.bincount(source, minlength=nodes).astype(float)
        pairs = set(zip(source.tolist(), destination.tolist()))
        reciprocal = sum((right, left) in pairs for left, right in pairs) / edges
        self_loop = float(np.mean(source == destination))
    else:
        indegree = outdegree = np.zeros(nodes, dtype=float)
        reciprocal = self_loop = 0.0
    density = edges / max(nodes * nodes, 1)
    return np.asarray([
        nodes, edges, density, self_loop, reciprocal,
        indegree.mean(), indegree.std(), indegree.max(initial=0),
        outdegree.mean(), outdegree.std(), outdegree.max(initial=0),
    ], dtype=float)


def _moments(values, width):
    if not len(values):
        return np.zeros(width * 4, dtype=float)
    return np.concatenate((values.mean(axis=0), values.std(axis=0),
                           values.min(axis=0), values.max(axis=0)))


def features(sample, mode='node_edge', periodic_clock=None, holdout=1):
    sample_targets(sample, holdout)
    if mode not in ('node', 'node_edge', 'feature_matched'):
        raise ValueError('Unknown baseline feature mode')
    windows = []
    for state in sample.states[:-holdout]:
        if state.x.ndim != 2 or state.x.shape[0] == 0:
            raise ValueError('History node features must be a nonempty matrix')
        x = state.x
        if periodic_clock is not None:
            from cybermind.models.periodic_input import PeriodicClockInput
            x = PeriodicClockInput(x.shape[1], periodic_clock)(x)
        node_values = x.detach().cpu().numpy()
        node = (node_values.mean(axis=0) if mode != 'feature_matched'
                else _moments(node_values, node_values.shape[1]))
        parts = [node]
        if mode in ('node_edge', 'feature_matched'):
            edge = state.edge_attr.detach().cpu().numpy()
            if edge.ndim != 2:
                raise ValueError('History edge features must be a matrix')
            parts.append((edge.mean(axis=0) if len(edge) else np.zeros(edge.shape[1], dtype=node.dtype))
                         if mode == 'node_edge' else _moments(edge, edge.shape[1]))
        if mode == 'feature_matched':
            parts.append(_topology_features(state))
        windows.append(np.concatenate(parts))
    vector = np.concatenate(windows)
    if not np.isfinite(vector).all():
        raise ValueError('Baseline features must be finite')
    return vector


def metric_report(targets, probabilities, threshold):
    if not 0 <= threshold <= 1:
        raise ValueError('threshold must lie in [0,1]')
    y, p = np.asarray(targets), np.asarray(probabilities)
    if y.ndim != 1 or p.shape != y.shape or not np.isin(y, [0, 1]).all():
        raise ValueError('Targets and probabilities must be aligned vectors with binary targets')
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError('Probabilities must be finite values in [0,1]')
    if len(y) == 0:
        return {name: None for name in ('f1', 'precision', 'recall', 'fpr', 'ap', 'roc_auc')}, {'tn': 0, 'fp': 0, 'fn': 0, 'tp': 0}
    metrics = binary_metrics(y, p, threshold)
    pred = p >= threshold
    counts = {name: int(mask.sum()) for name, mask in {
        'tn': (y == 0) & ~pred, 'fp': (y == 0) & pred,
        'fn': (y == 1) & ~pred, 'tp': (y == 1) & pred}.items()}
    if counts['tn'] + counts['fp'] == 0:
        metrics['fpr'] = None
    metrics['roc_auc'] = float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else None
    return metrics, counts


def evaluate_baseline(processed, split='test', mode='node_edge', threshold=0.5, periodic_clock=None):
    if split not in ('val', 'test'):
        raise ValueError('Evaluate on a held-out val or test split')
    processed = Path(processed)
    training = GraphSequenceDataset(processed / 'train.pt')
    evaluation = GraphSequenceDataset(processed / f'{split}.pt')
    if not len(training):
        raise ValueError('No training sequences')
    xtrain = np.stack([features(s, mode, periodic_clock) for s in training])
    ytrain = np.array([sample_target(s) for s in training])
    targets = [sample_target(s) for s in evaluation]
    xevaluation = np.stack([features(s, mode, periodic_clock) for s in evaluation]) if len(evaluation) else np.empty((0, xtrain.shape[1]))
    if xevaluation.shape[1] != xtrain.shape[1]:
        raise ValueError('Training and evaluation feature widths differ')
    if len(np.unique(ytrain)) == 1:
        model_name = 'dummy_prior_single_class'
        probabilities = np.full(len(evaluation), float(ytrain.mean()))
    else:
        model_name = 'logistic_regression'
        model = LogisticBaseline().fit(xtrain, ytrain)
        probabilities = model.predict_proba(xevaluation) if len(evaluation) else np.array([])
    metrics, counts = metric_report(targets, probabilities, threshold)
    state = training[0].states[0]
    registry = {
        'feature_mode': mode, 'node_columns': int(state.x.shape[1]),
        'edge_columns': int(state.edge_attr.shape[1]) if mode in ('node_edge', 'feature_matched') else 0,
        'history_windows': len(training[0].states) - 1,
        'flattened_width': int(xtrain.shape[1]),
        'graph_topology': 'summary statistics' if mode == 'feature_matched' else False,
        'aggregations': ['mean', 'std', 'min', 'max'] if mode == 'feature_matched' else ['mean'],
        'periodic_clock': periodic_clock,
        'periodic_columns': 2 if periodic_clock is not None else 0,
        'normalization_sha256': sha256(processed / 'normalization.json') if (processed / 'normalization.json').exists() else None,
    }
    if (processed / 'normalization.json').exists():
        normalizer = json.loads((processed / 'normalization.json').read_text(encoding='utf-8'))
        registry['node_features'] = normalizer['node']['features']
        registry['edge_features'] = normalizer['edge']['features'] if mode in ('node_edge', 'feature_matched') else []
    return {
        'baseline': model_name, 'split': split, 'threshold': threshold,
        'protocol': PROTOCOL, 'protocol_sha256': record_hash(PROTOCOL),
        'feature_registry': registry, 'feature_registry_sha256': record_hash(registry),
        'source_sha256': {name: sha256(processed / f'{name}.pt') for name in ('train', split)},
        'training_count': len(training), 'evaluation_count': len(evaluation),
        'training_target_counts': {'negative': int((ytrain == 0).sum()),
                                   'positive': int((ytrain == 1).sum())},
        'metrics': metrics, 'confusion_counts': counts,
        'per_sample': [{'scenario': s.scenario_id, 'target_timestamp': float(s.states[-1].timestamp),
                        'target': y, 'predicted_future_risk': float(p)}
                       for s, y, p in zip(evaluation, targets, probabilities)],
    }


def evaluate_baseline_multistep(processed, split='test', mode='feature_matched',
                                threshold=0.5, horizon=4, periodic_clock=None):
    """Fit one leakage-safe logistic head per future step from one observed prefix."""
    if split not in ('val', 'test'):
        raise ValueError('Evaluate on a held-out val or test split')
    processed = Path(processed)
    training = GraphSequenceDataset(processed / 'train.pt')
    evaluation = GraphSequenceDataset(processed / f'{split}.pt')
    if not len(training) or not len(evaluation):
        raise ValueError('Training and evaluation sequences must be nonempty')
    xtrain = np.stack([features(s, mode, periodic_clock, holdout=horizon) for s in training])
    xevaluation = np.stack([features(s, mode, periodic_clock, holdout=horizon) for s in evaluation])
    if xevaluation.shape[1] != xtrain.shape[1]:
        raise ValueError('Training and evaluation feature widths differ')
    train_targets = np.asarray([sample_targets(s, horizon) for s in training], dtype=int)
    eval_targets = np.asarray([sample_targets(s, horizon) for s in evaluation], dtype=int)
    per_horizon = []
    probability_columns = []
    for step in range(horizon):
        ytrain = train_targets[:, step]
        if len(np.unique(ytrain)) == 1:
            name = 'dummy_prior_single_class'
            probabilities = np.full(len(evaluation), float(ytrain.mean()))
        else:
            name = 'logistic_regression'
            probabilities = LogisticBaseline().fit(xtrain, ytrain).predict_proba(xevaluation)
        metrics, counts = metric_report(eval_targets[:, step], probabilities, threshold)
        probability_columns.append(probabilities)
        per_horizon.append({'step': step + 1, 'baseline': name, 'metrics': metrics,
                            'confusion_counts': counts,
                            'training_target_counts': {
                                'negative': int((ytrain == 0).sum()),
                                'positive': int((ytrain == 1).sum())}})
    probability_matrix = np.stack(probability_columns, axis=1)
    pooled_metrics, pooled_counts = metric_report(eval_targets.ravel(), probability_matrix.ravel(), threshold)
    state = training[0].states[0]
    registry = {
        'feature_mode': mode, 'node_columns': int(state.x.shape[1]),
        'edge_columns': int(state.edge_attr.shape[1]) if mode in ('node_edge', 'feature_matched') else 0,
        'observed_windows': len(training[0].states) - horizon,
        'forecast_horizon_windows': horizon, 'flattened_width': int(xtrain.shape[1]),
        'graph_topology': 'summary statistics' if mode == 'feature_matched' else False,
        'aggregations': ['mean', 'std', 'min', 'max'] if mode == 'feature_matched' else ['mean'],
        'periodic_clock': periodic_clock,
    }
    return {
        'baseline': 'per_horizon_logistic_regression', 'split': split,
        'threshold': threshold, 'forecast_horizon_windows': horizon,
        'protocol': PROTOCOL, 'protocol_sha256': record_hash(PROTOCOL),
        'feature_registry': registry, 'feature_registry_sha256': record_hash(registry),
        'source_sha256': {name: sha256(processed / f'{name}.pt') for name in ('train', split)},
        'training_count': len(training), 'evaluation_count': len(evaluation),
        'metrics': pooled_metrics, 'confusion_counts': pooled_counts,
        'per_horizon': per_horizon,
        'per_sample': [
            {'scenario': sample.scenario_id,
             'target_timestamps': [float(state.timestamp) for state in sample.states[-horizon:]],
             'targets': targets.tolist(), 'predicted_future_risk': probabilities.tolist()}
            for sample, targets, probabilities in zip(evaluation, eval_targets, probability_matrix)
        ],
    }
