#!/usr/bin/env python3
"""Deterministically compare real graph identities/edges with canonical flows."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.data.graph_builder import build_graph_state


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def audit_date(directory, date):
    files = sorted((directory / date).glob('*.parquet'))
    if not files:
        raise ValueError(f'{date}: no canonical parquet files')
    frame = pd.concat([pd.read_parquet(path) for path in files], ignore_index=True)
    frame['timestamp'] = pd.to_datetime(frame.timestamp, utc=True)
    attacks = frame.loc[pd.to_numeric(frame.attack_stage, errors='coerce').fillna(0).ne(0)]
    anchor = (attacks.timestamp.min() if not attacks.empty else frame.timestamp.min())
    window = frame.loc[(frame.timestamp >= anchor) & (frame.timestamp < anchor + pd.Timedelta(seconds=60))].copy()
    window['stage'] = pd.to_numeric(window.attack_stage, errors='coerce').fillna(6).astype(int)
    window['infiltration'] = window.stage.ne(0).astype(float)
    state = build_graph_state(window, f'R2-{date}', {
        'window_start': float(anchor.timestamp()),
        'window_end': float(anchor.timestamp() + 60),
    })
    expected_nodes = sorted(set(window.src.astype(str)) | set(window.dst.astype(str)))
    expected_pairs = set(zip(window.src.astype(str), window.dst.astype(str)))
    actual_pairs = {
        (state.node_ids[int(src)], state.node_ids[int(dst)])
        for src, dst in state.edge_index.t().tolist()
    }
    aggregates = window.assign(
        expected_bytes=pd.to_numeric(window.bytes_fwd) + pd.to_numeric(window.bytes_bwd),
        expected_packets=pd.to_numeric(window.packets_fwd) + pd.to_numeric(window.packets_bwd),
    ).groupby(['src', 'dst'])[['expected_bytes', 'expected_packets']].sum()
    numeric_mismatches = []
    for index, (src, dst) in enumerate(state.edge_index.t().tolist()):
        pair = (state.node_ids[int(src)], state.node_ids[int(dst)])
        expected = aggregates.loc[pair]
        actual = state.edge_attr[index]
        if not (np.isclose(float(actual[0]), float(expected.expected_bytes), rtol=1e-5, atol=1e-4) and
                np.isclose(float(actual[1]), float(expected.expected_packets), rtol=1e-5, atol=1e-4)):
            numeric_mismatches.append(pair)
    passed = (state.node_ids == expected_nodes and actual_pairs == expected_pairs and not numeric_mismatches)
    return {
        'date': date,
        'canonical_files': [{'path': str(path), 'sha256': sha256(path)} for path in files],
        'anchor_utc': anchor.isoformat(),
        'window_rows': len(window),
        'stage_ids': sorted(pd.to_numeric(window.attack_stage).astype(int).unique().tolist()),
        'source_node_count': len(expected_nodes),
        'graph_node_count': len(state.node_ids),
        'source_directed_pair_count': len(expected_pairs),
        'graph_directed_edge_count': state.edge_index.shape[1],
        'missing_pairs': sorted([list(pair) for pair in expected_pairs - actual_pairs]),
        'extra_pairs': sorted([list(pair) for pair in actual_pairs - expected_pairs]),
        'numeric_mismatch_pairs': [list(pair) for pair in numeric_mismatches],
        'sample_edges': [list(pair) for pair in sorted(actual_pairs)[:5]],
        'passed': passed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/intermediate_real_chunk_r2')
    parser.add_argument('--output', default='examples/real_data_validation/r2/graph_identity_audit.json')
    args = parser.parse_args()
    source = ROOT / args.input
    records = [audit_date(source, date) for date in ('2018-02-14', '2018-03-01', '2018-03-02')]
    result = {
        'passed': all(record['passed'] for record in records),
        'selection': 'first corrected non-Benign-stage flow per frozen date; 60-second half-open window',
        'records': records,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
