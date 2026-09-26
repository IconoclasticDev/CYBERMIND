#!/usr/bin/env python3
"""Audit mixed-class, chronology and stage support in prepared graph splits."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.data.dataset import GraphSequenceDataset


def summarize(dataset):
    terminal = Counter(int(sample.states[-1].y_infiltration > 0) for sample in dataset)
    terminal_stages = Counter(int(sample.states[-1].y_stage) for sample in dataset)
    all_stages = Counter(int(state.y_stage) for sample in dataset for state in sample.states)
    timestamps = [state.timestamp for sample in dataset for state in sample.states]
    return {
        'sequences': len(dataset),
        'terminal_targets': {'benign': terminal[0], 'attack': terminal[1]},
        'terminal_stages': {str(key): value for key, value in sorted(terminal_stages.items())},
        'all_window_stages': {str(key): value for key, value in sorted(all_stages.items())},
        'start_timestamp': min(timestamps), 'end_timestamp': max(timestamps),
    }


def audit(processed):
    processed = Path(processed)
    splits = {name: GraphSequenceDataset(processed / f'{name}.pt')
              for name in ('train', 'val', 'test')}
    rows = {name: summarize(dataset) for name, dataset in splits.items()}
    mixed = {name: row['terminal_targets']['benign'] > 0 and row['terminal_targets']['attack'] > 0
             for name, row in rows.items()}
    chronological = (rows['train']['end_timestamp'] < rows['val']['start_timestamp'] <
                     rows['val']['end_timestamp'] < rows['test']['start_timestamp'])
    required_attack_stages = {1, 2, 3, 4, 5}
    support = {name: {int(key) for key, value in row['all_window_stages'].items() if value > 0}
               for name, row in rows.items()}
    missing = {name: sorted(required_attack_stages - stages) for name, stages in support.items()}
    return {
        'processed_dir': str(processed), 'splits': rows,
        'mixed_terminal_classes': mixed, 'strictly_chronological': chronological,
        'missing_attack_stages': missing,
        'gates': {
            'binary_forecasting_ready': chronological and mixed['train'] and mixed['val'] and mixed['test'],
            'validation_fpr_ready': mixed['val'],
            'unseen_stage_4_test': 4 not in support['train'] and 4 in support['test'],
            'comprehensive_stage_training_ready': not missing['train'],
        },
        'decision': ('BLOCK comprehensive stage training; acquire authoritative missing-stage data.'
                     if missing['train'] else 'Stage-support gate passed.'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--processed', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = audit(ROOT / args.processed)
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
