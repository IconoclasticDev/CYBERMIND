"""Verify the R1 labeled real-chunk artifacts without changing their gate."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.data.pcap_extract import PACKET_FEATURES
from cybermind.data.real_chunk_export import PROVENANCE_LABEL
from cybermind.data.real_chunk_label import CORRECTED_SOURCE, LABEL_METHOD, ORIGINAL_SOURCE

MANIFEST = ROOT / 'data/manifests/r1_real_chunk_files.csv'
RUN_AUDIT = ROOT / 'examples/real_data_validation/r1/labeling_audit.json'
OUTPUT = ROOT / 'examples/real_data_validation/r1/output_audit.json'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError('Preserve existing R1 output audit')
    records = list(csv.DictReader(MANIFEST.open(encoding='utf-8')))
    run = json.loads(RUN_AUDIT.read_text(encoding='utf-8'))
    details = []
    totals = dict(rows=0, invalid_packet_rows=0, invalid_label_rows=0,
                  invalid_stage_rows=0, bad_provenance_rows=0,
                  discrepancy_rows=0, unresolved_refinement_rows=0)
    for record in records:
        path = ROOT / record['output_path']
        if digest(path) != record['output_sha256']:
            raise ValueError(f'Output hash mismatch: {path}')
        local = {key: 0 for key in totals}
        for frame in pd.read_csv(path, chunksize=100_000, low_memory=False):
            local['rows'] += len(frame)
            required = {
                'label', 'stage', 'infiltration', 'label_verified',
                'label_refinement_verified', 'corrected_rule_id',
                'corrected_refinement_status', 'original_cic_label',
                'original_rule_id', 'label_discrepancy', 'label_method',
                'corrected_rule_source', 'original_rule_source',
                'flow_feature_source', *PACKET_FEATURES,
            }
            missing = required - set(frame)
            if missing:
                raise ValueError(f'{path}: missing {sorted(missing)}')
            packet = frame[list(PACKET_FEATURES)].apply(pd.to_numeric, errors='coerce')
            local['invalid_packet_rows'] += int((~np.isfinite(packet).all(axis=1)
                                                  | ~packet.packet_features_available.eq(1)).sum())
            label = frame.label.fillna('').astype(str).str.strip()
            verified = frame.label_verified.astype(str).str.lower().isin(['true', '1'])
            local['invalid_label_rows'] += int((label.eq('') | ~verified).sum())
            stage = pd.to_numeric(frame.stage, errors='coerce')
            infiltration = pd.to_numeric(frame.infiltration, errors='coerce')
            local['invalid_stage_rows'] += int((~stage.isin(range(7))
                                                 | infiltration.ne(stage.ne(0).astype(float))).sum())
            bad = (frame.flow_feature_source.ne(PROVENANCE_LABEL)
                   | frame.label_method.ne(LABEL_METHOD)
                   | frame.corrected_rule_source.ne(CORRECTED_SOURCE)
                   | frame.original_rule_source.ne(ORIGINAL_SOURCE))
            local['bad_provenance_rows'] += int(bad.sum())
            discrepancy = frame.label.ne(frame.original_cic_label)
            stored_discrepancy = frame.label_discrepancy.astype(str).str.lower().isin(['true', '1'])
            local['invalid_label_rows'] += int(discrepancy.ne(stored_discrepancy).sum())
            local['discrepancy_rows'] += int(discrepancy.sum())
            unresolved = frame.corrected_refinement_status.ne('complete')
            refinement_verified = frame.label_refinement_verified.astype(str).str.lower().isin(['true', '1'])
            local['invalid_label_rows'] += int(unresolved.eq(refinement_verified).sum())
            local['unresolved_refinement_rows'] += int(unresolved.sum())
        if local['rows'] != int(record['rows']):
            raise ValueError(f'Row count mismatch: {path}')
        for key in totals:
            totals[key] += local[key]
        details.append({'date': record['date'], 'output': record['output_path'], **local})
    blocking = sum(totals[key] for key in (
        'invalid_packet_rows', 'invalid_label_rows', 'invalid_stage_rows', 'bad_provenance_rows'))
    if totals['rows'] != run['rows'] or totals['discrepancy_rows'] != run['discrepancy_rows']:
        raise ValueError('Run audit totals do not match output recomputation')
    result = {
        'passed': blocking == 0 and len(records) == 15,
        'broad_label_and_stage_complete': blocking == 0,
        'fine_grained_refinement_complete': totals['unresolved_refinement_rows'] == 0,
        'output_count': len(records), 'totals': totals, 'records': details,
        'manifest_sha256': digest(MANIFEST), 'run_audit_sha256': digest(RUN_AUDIT),
        'methodology_sha256': digest(ROOT / 'data/real_chunk/LABELING_METHODOLOGY.md'),
        'refinement_limitation': (
            'Broad Botnet Ares labels and Command & Control stages are verified. '
            'Fine-grained attempted categories remain unresolved where the approved '
            'directional R0 schema lacks backward RST and reverse payload totals.'
        ),
        'lateral_movement_disclosure': (
            'Real-chunk validation does not include a Lateral Movement transition. '
            'Kill-chain-diversity validation on real data covers the other represented '
            'stages only; it does not validate Lateral Movement.'
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
