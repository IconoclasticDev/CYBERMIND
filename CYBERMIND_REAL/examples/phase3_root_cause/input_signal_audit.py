"""Read-only numerical audit of the ORIGINAL Phase 3 integration fixture."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import pandas as pd
import torch
from cybermind.data.graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES

SOURCE = ROOT / 'examples/phase3_joint/combined'


def feature_stats(states, attribute, names):
    # Preserve node/edge coordinate positions; do not pool away a possible signal.
    arrays = np.stack([getattr(s, attribute).numpy().astype('float64') for s in states])
    labels = np.array([s.y_stage for s in states])
    feature_std = arrays.std(axis=0)
    times = np.array([s.timestamp for s in states])
    records = []
    for feature in range(arrays.shape[-1]):
        varying = bool((feature_std[:, feature] > 1e-12).any())
        if varying:
            coordinate = arrays[:, 0, feature]
            means = {str(c): float(coordinate[labels == c].mean()) for c in sorted(set(labels))}
            records.append(dict(name=names[feature], column=feature,
                per_entity_std=feature_std[:, feature].tolist(), first_entity_class_means=means,
                correlation_with_time=float(np.corrcoef(coordinate, times)[0, 1]),
                class_1_minus_0_mean_over_overall_std=float((means['1']-means['0'])/coordinate.std())))
    adjacent = []
    for index in range(len(states)-1):
        if labels[index] != labels[index+1] and times[index+1]-times[index] == 1:
            adjacent.append(float(np.linalg.norm(arrays[index+1]-arrays[index])))
    return dict(shape=list(arrays.shape), varying_feature_count=len(records),
        constant_feature_count=arrays.shape[-1]-len(records), varying_features=records,
        adjacent_different_label_pairs=len(adjacent),
        adjacent_different_label_l2_min=min(adjacent) if adjacent else None,
        adjacent_different_label_l2_max=max(adjacent) if adjacent else None)


def main():
    result = dict(source=str(SOURCE.relative_to(ROOT)), synthetic_only=True,
        read_only_original_fixture=True, prototype_features_added=False,
        interpretation='Numerical signal audit, not a proof of unlearnability. Byte volume monotonically encodes time, so periodic labels are theoretically recoverable from time-correlated volume. No prototype fixture is used.',
        splits={}, source_sha256={})
    raw_paths = sorted((SOURCE/'raw').glob('*.csv'))
    raw = pd.concat([pd.read_csv(p) for p in raw_paths], ignore_index=True).sort_values('timestamp')
    nonlabel_columns = [c for c in raw.columns if c != 'label']
    attack_groups = [g for _, g in raw.groupby('timestamp') if g['label'].nunique() > 1]
    result['raw'] = dict(rows=len(raw), unique_seconds=raw.timestamp.nunique(),
        label_counts={str(k): int(v) for k,v in raw.label.value_counts().items()},
        within_second_mixed_label_groups=len(attack_groups),
        mixed_label_groups_with_identical_all_nonlabel_columns=sum(int(g[nonlabel_columns].nunique().max() == 1) for g in attack_groups),
        varying_nonlabel_columns=[c for c in nonlabel_columns if raw[c].nunique()>1],
        label_rule='PORTSCAN exactly when second % 4 == 0 and flow == 1; all other flow labels BENIGN')
    for split in ('train','val','test'):
        path = SOURCE/'processed'/f'{split}.pt'
        samples = torch.load(path, map_location='cpu', weights_only=False)
        unique = {(s.scenario_id, s.timestamp):s for sample in samples for s in sample.states}
        states = sorted(unique.values(), key=lambda s:s.timestamp)
        result['splits'][split] = dict(sequence_count=len(samples), unique_windows=len(states),
            window_stage_counts=dict(Counter(str(s.y_stage) for s in states)),
            supervision_stage_counts=dict(Counter(str(s.y_stage) for sample in samples for s in sample.states[1:])),
            time_range=[states[0].timestamp,states[-1].timestamp],
            node=feature_stats(states,'x',NODE_FEATURE_NAMES),
            edge=feature_stats(states,'edge_attr',EDGE_FEATURE_NAMES),
            all_topologies_identical=all(torch.equal(states[0].edge_index,s.edge_index) for s in states))
    for path in [*raw_paths,*(SOURCE/'processed').glob('*.pt')]:
        result['source_sha256'][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    destination = Path(__file__).with_name('input_signal.json')
    destination.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
