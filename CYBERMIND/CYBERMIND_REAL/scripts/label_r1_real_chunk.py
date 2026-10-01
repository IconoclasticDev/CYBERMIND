"""Atomically label every audited R0 CSV with corrected and original rules."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.data.real_chunk_label import (
    CORRECTED_SOURCE, LABEL_METHOD, ORIGINAL_SOURCE, corrected_labels,
    original_labels, stage_for_label,
)

R0_MANIFEST = ROOT / 'data/manifests/r0_real_chunk_files.csv'
R1_MANIFEST = ROOT / 'data/manifests/r1_real_chunk_files.csv'
AUDIT = ROOT / 'examples/real_data_validation/r1/labeling_audit.json'
DISCREPANCIES = ROOT / 'examples/real_data_validation/r1/discrepancies.csv'
RULE_FILES = [
    ROOT / 'data/real_chunk/rules/Distrinet_CICIDS2018_fixed_f0ce502.ipynb',
    ROOT / 'data/real_chunk/rules/Distrinet_CSECICIDS2018.html',
    ROOT / 'data/real_chunk/rules/UNB_CSE_CIC_IDS2018.html',
]


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main() -> None:
    if R1_MANIFEST.exists() or AUDIT.exists() or DISCREPANCIES.exists():
        raise FileExistsError('Preserve existing R1 manifest/audit/discrepancy evidence')
    records = list(csv.DictReader(R0_MANIFEST.open(encoding='utf-8')))
    if len(records) != 15:
        raise ValueError('R0 manifest must contain all 15 frozen outputs')
    output_records, label_counts, original_counts, pair_counts, refinement_counts = [], {}, {}, {}, {}
    total_rows = total_discrepancies = 0
    for record in records:
        source = ROOT / record['output_path']
        if digest(source) != record['output_sha256']:
            raise ValueError(f'R0 input hash mismatch: {source}')
        output = ROOT / 'data/real_chunk/labeled' / record['date'] / source.name
        partial = output.with_name(output.name + '.partial')
        report = ROOT / 'examples/real_data_validation/r1/exports' / record['date'] / (source.stem + '.json')
        report_partial = report.with_name(report.name + '.partial')
        if any(path.exists() for path in (output, partial, report, report_partial)):
            raise FileExistsError(f'Preserve existing R1 output/report: {output}')
        output.parent.mkdir(parents=True, exist_ok=True)
        report.parent.mkdir(parents=True, exist_ok=True)
        rows = discrepancies = 0
        first_chunk = True
        local_labels, local_original, local_refinements = {}, {}, {}
        for frame in pd.read_csv(source, chunksize=100_000, low_memory=False):
            corrected = corrected_labels(frame)
            original = original_labels(frame)
            labeled = pd.concat([frame, corrected, original], axis=1)
            labeled['stage'] = stage_for_label(labeled.label)
            labeled['infiltration'] = labeled.stage.ne(0).astype(float)
            labeled['label_verified'] = True
            labeled['label_refinement_verified'] = labeled.corrected_refinement_status.eq('complete')
            labeled['label_method'] = LABEL_METHOD
            labeled['corrected_rule_source'] = CORRECTED_SOURCE
            labeled['original_rule_source'] = ORIGINAL_SOURCE
            labeled['label_discrepancy'] = labeled.label.ne(labeled.original_cic_label)
            labeled.to_csv(partial, mode='w' if first_chunk else 'a', header=first_chunk,
                           index=False, encoding='utf-8')
            first_chunk = False
            rows += len(labeled)
            discrepancies += int(labeled.label_discrepancy.sum())
            for key, value in labeled.label.value_counts().items():
                local_labels[str(key)] = local_labels.get(str(key), 0) + int(value)
                label_counts[(record['date'], str(key))] = label_counts.get((record['date'], str(key)), 0) + int(value)
            for key, value in labeled.original_cic_label.value_counts().items():
                local_original[str(key)] = local_original.get(str(key), 0) + int(value)
                original_counts[(record['date'], str(key))] = original_counts.get((record['date'], str(key)), 0) + int(value)
            for key, value in labeled.corrected_refinement_status.value_counts().items():
                local_refinements[str(key)] = local_refinements.get(str(key), 0) + int(value)
                refinement_counts[(record['date'], str(key))] = refinement_counts.get((record['date'], str(key)), 0) + int(value)
            pairs = labeled.groupby(['label', 'original_cic_label'], dropna=False).size()
            for key, value in pairs.items():
                pair_key = (record['date'], str(key[0]), str(key[1]))
                pair_counts[pair_key] = pair_counts.get(pair_key, 0) + int(value)
        if rows != int(record['rows']):
            raise ValueError(f'R1 row preservation failed: {source}')
        output_hash = digest(partial)
        report_record = {
            'status': 'complete_r1_labels', 'date': record['date'],
            'r0_input': record['output_path'], 'r0_input_sha256': record['output_sha256'],
            'output': str(output.relative_to(ROOT)), 'output_sha256': output_hash,
            'rows': rows, 'discrepancies': discrepancies,
            'corrected_label_counts': local_labels, 'original_label_counts': local_original,
            'refinement_status_counts': local_refinements,
            'label_method': LABEL_METHOD, 'corrected_rule_source': CORRECTED_SOURCE,
            'original_rule_source': ORIGINAL_SOURCE,
        }
        report_partial.write_text(json.dumps(report_record, indent=2) + '\n', encoding='utf-8')
        partial.replace(output)
        report_partial.replace(report)
        total_rows += rows
        total_discrepancies += discrepancies
        output_records.append({
            'date': record['date'], 'r0_input_path': record['output_path'],
            'r0_input_sha256': record['output_sha256'],
            'output_path': str(output.relative_to(ROOT)), 'output_bytes': output.stat().st_size,
            'output_sha256': output_hash, 'rows': rows,
        })

    R1_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with R1_MANIFEST.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output_records[0]))
        writer.writeheader(); writer.writerows(output_records)
    DISCREPANCIES.parent.mkdir(parents=True, exist_ok=True)
    with DISCREPANCIES.open('x', encoding='utf-8', newline='') as stream:
        fields = ['date', 'corrected_label', 'original_cic_label', 'rows']
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for (date, corrected, original), count in sorted(pair_counts.items()):
            writer.writerow(dict(date=date, corrected_label=corrected,
                                 original_cic_label=original, rows=count))
    result = {
        'passed': True, 'output_count': len(output_records), 'rows': total_rows,
        'discrepancy_rows': total_discrepancies,
        'r0_manifest_sha256': digest(R0_MANIFEST),
        'r1_manifest': str(R1_MANIFEST.relative_to(ROOT)),
        'r1_manifest_sha256': digest(R1_MANIFEST),
        'discrepancy_log': str(DISCREPANCIES.relative_to(ROOT)),
        'discrepancy_log_sha256': digest(DISCREPANCIES),
        'rule_files': [{'path': str(path.relative_to(ROOT)), 'sha256': digest(path)} for path in RULE_FILES],
        'corrected_counts': [dict(date=k[0], label=k[1], rows=v) for k, v in sorted(label_counts.items())],
        'original_counts': [dict(date=k[0], label=k[1], rows=v) for k, v in sorted(original_counts.items())],
        'refinement_counts': [dict(date=k[0], status=k[1], rows=v) for k, v in sorted(refinement_counts.items())],
        'label_method': LABEL_METHOD,
        'fallback_feature_disclosure': (
            "flow_feature_source: CYBERMIND custom directional packet exporter; 40-column schema; "
            "satisfies the project's 20-field packet-feature contract when verified, but is not "
            "CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter traffic-statistic "
            "columns. No CICFlowMeter feature parity is claimed."
        ),
        'lateral_movement_disclosure': (
            'Real-chunk validation does not include a Lateral Movement transition. '
            'Kill-chain-diversity validation on real data covers the other represented stages '
            'only; it does not validate Lateral Movement.'
        ),
    }
    AUDIT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
