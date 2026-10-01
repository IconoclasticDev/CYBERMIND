#!/usr/bin/env python3
"""Audit the completed R2 canonical and prepared artifacts without sampling rows."""
from collections import Counter
from pathlib import Path
import hashlib
import ipaddress
import json
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.data.dataset import GraphSequenceDataset


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    canonical_report_path = ROOT / 'examples/real_data_validation/r2/canonical_strict_validation.json'
    input_report_path = ROOT / 'examples/real_data_validation/r2/r1_strict_validation.json'
    graph_report_path = ROOT / 'examples/real_data_validation/r2/graph_identity_audit.json'
    processed = ROOT / 'data/processed_real_chunk_r2'
    metadata = json.loads((processed / 'metadata.json').read_text(encoding='utf-8'))
    canonical = json.loads(canonical_report_path.read_text(encoding='utf-8'))
    inputs = json.loads(input_report_path.read_text(encoding='utf-8'))
    graph = json.loads(graph_report_path.read_text(encoding='utf-8'))
    split_records = []
    total_sequences = 0
    for split in ('train', 'val', 'test'):
        dataset = GraphSequenceDataset(processed / f'{split}.pt')
        total_sequences += len(dataset)
        stages = Counter()
        invalid_ip_nodes = 0
        nonfinite_states = 0
        gap_violations = 0
        fingerprint_failures = 0
        for sample in dataset.samples:
            starts = [state.metadata['window_start'] for state in sample.states]
            gap_violations += sum((b - a) > 30.000001 for a, b in zip(starts, starts[1:]))
            for state in sample.states:
                stages[int(state.y_stage)] += 1
                nonfinite_states += int(not (torch.isfinite(state.x).all() and torch.isfinite(state.edge_attr).all()))
                fingerprint_failures += int(state.metadata.get('normalization_fingerprint') != metadata['normalization_fingerprint'])
                for node in state.node_ids:
                    try:
                        ipaddress.ip_address(node)
                    except ValueError:
                        invalid_ip_nodes += 1
        split_records.append({
            'split': split,
            'sequences': len(dataset),
            'state_occurrences': sum(stages.values()),
            'stage_occurrence_counts': {str(key): value for key, value in sorted(stages.items())},
            'invalid_ip_node_occurrences': invalid_ip_nodes,
            'nonfinite_state_occurrences': nonfinite_states,
            'history_gap_violations': gap_violations,
            'normalization_fingerprint_failures': fingerprint_failures,
            'sha256': sha256(processed / f'{split}.pt'),
        })
    all_canonical_pass = bool(canonical) and all(row.get('passed') for row in canonical)
    all_input_pass = bool(inputs) and all(row.get('passed') for row in inputs)
    audited_rows = sum(row.get('rows_checked', 0) for row in canonical)
    all_splits_pass = all(
        not row['invalid_ip_node_occurrences'] and not row['nonfinite_state_occurrences'] and
        not row['history_gap_violations'] and not row['normalization_fingerprint_failures']
        for row in split_records
    )
    result = {
        'passed': all_input_pass and all_canonical_pass and audited_rows == 1186046 and
                  graph.get('passed') is True and total_sequences == metadata['num_sequences'] and all_splits_pass,
        'r1_input_strict_pass': all_input_pass,
        'canonical_strict_pass': all_canonical_pass,
        'canonical_rows_checked': audited_rows,
        'expected_rows': 1186046,
        'graph_identity_pass': graph.get('passed'),
        'metadata_num_sequences': metadata['num_sequences'],
        'audited_num_sequences': total_sequences,
        'packet_feature_coverage_by_split': {
            report['split']: report['packet_feature_coverage'] for report in metadata['reports']
        },
        'normalization_fingerprint': metadata['normalization_fingerprint'],
        'artifacts': {
            'adapter_report_sha256': sha256(ROOT / 'data/intermediate_real_chunk_r2/adapter_report.json'),
            'metadata_sha256': sha256(processed / 'metadata.json'),
            'normalization_sha256': sha256(processed / 'normalization.json'),
            'r1_input_validation_sha256': sha256(input_report_path),
            'canonical_validation_sha256': sha256(canonical_report_path),
            'graph_identity_audit_sha256': sha256(graph_report_path),
        },
        'splits': split_records,
        'fallback_feature_disclosure': "flow_feature_source: CYBERMIND custom directional packet exporter; 40-column schema; satisfies the project's 20-field packet-feature contract when verified, but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter traffic-statistic columns. No CICFlowMeter feature parity is claimed.",
        'lateral_movement_disclosure': 'Real-chunk validation does not include a Lateral Movement transition. Kill-chain-diversity validation on real data covers the other represented stages only; it does not validate Lateral Movement.',
    }
    output = ROOT / 'examples/real_data_validation/r2/output_audit.json'
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
