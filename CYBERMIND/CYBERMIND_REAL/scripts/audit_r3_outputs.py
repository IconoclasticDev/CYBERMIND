#!/usr/bin/env python3
"""Validate every R3 per-window zero-shot record and reconcile its summary."""
from collections import Counter
from pathlib import Path
import gzip
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]
R3 = ROOT / 'examples/real_data_validation/r3'
QUALIFIER = 'source: zero-shot, synthetic-trained weights, real-corpus chunk — out-of-distribution test'


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    summary_path = R3 / 'summary.json'
    rows_path = R3 / 'per_window_predictions.jsonl.gz'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    decoded = [Counter() for _ in range(4)]
    observed = Counter()
    failures = Counter()
    count = 0
    with gzip.open(rows_path, 'rt', encoding='utf-8') as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            count += 1
            failures['qualifier'] += int(row.get('source_qualifier') != QUALIFIER)
            failures['step_count'] += int(len(row.get('predictions', [])) != 4)
            observed.update(map(int, row.get('observed_target_stages', [])))
            for index, prediction in enumerate(row.get('predictions', [])):
                probabilities = prediction['stage_probabilities']
                decoded[index][int(prediction['decoded_stage'])] += 1
                failures['nonfinite'] += int(not all(math.isfinite(float(value)) for value in probabilities + [
                    prediction['stage_confidence'], prediction['infiltration_probability'],
                    prediction['infiltration_variance']]))
                failures['probability_sum'] += int(abs(sum(probabilities) - 1.0) > 1e-5)
                failures['confidence'] += int(abs(max(probabilities) - prediction['stage_confidence']) > 1e-6)
                failures['illegal'] += int(bool(prediction['illegal_incoming_transition']))
    expected = [{int(key): value for key, value in step['decoded_stage_histogram'].items()}
                for step in summary['per_step']]
    failures['sample_count'] += int(count != summary['samples'])
    failures['prediction_hash'] += int(sha256(rows_path) != summary['predictions_sha256'])
    failures['summary_qualifier'] += int(summary.get('source_qualifier') != QUALIFIER)
    failures['contract'] += int(summary.get('preprocessing_contract', {}).get('passed') is not True)
    failures['histogram'] += sum(dict(decoded[index]) != expected[index] for index in range(4))
    result = {
        'passed': not any(failures.values()),
        'source_qualifier': QUALIFIER,
        'samples_checked': count,
        'prediction_records_sha256': sha256(rows_path),
        'summary_sha256': sha256(summary_path),
        'observed_history_stage_occurrence_counts': {str(key): value for key, value in sorted(observed.items())},
        'decoded_stage_counts_by_step': [
            {str(key): value for key, value in sorted(step.items())} for step in decoded
        ],
        'failure_counts': dict(failures),
        'lateral_movement_disclosure': 'Real-chunk validation does not include a Lateral Movement transition. Kill-chain-diversity validation on real data covers the other represented stages only; it does not validate Lateral Movement.',
    }
    output = R3 / 'output_audit.json'
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
