"""Verify and hash every frozen R0 input and unlabeled fallback CSV."""
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

PLAN = ROOT / 'examples/real_data_validation/r0/capture_scope_frozen.json'
OUTPUT = ROOT / 'data/manifests/r0_real_chunk_files.csv'
AUDIT = ROOT / 'examples/real_data_validation/r0/fallback_output_audit.json'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def expected_sources():
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    feb = json.loads((ROOT / plan['feb14_evidence']).read_text(encoding='utf-8'))
    records = [{
        'date': '2018-02-14', 'path': plan['feb14_input'],
        'sha256': feb['derivative_sha256'],
        'member': 'reviewed complete-record derivative of pcap/UCAP172.31.69.25',
    }]
    for item in plan['additional_members']:
        evidence_path = (ROOT / item['target']).with_suffix('.acquisition.json')
        evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
        records.append({'date': item['date'], 'path': item['target'],
                        'sha256': evidence['target_sha256'], 'member': item['member']['name']})
    return records


def audit_csv(path, expected_source_hash, expected_date, expected_member):
    rows = invalid_tuple = invalid_packet = bad_provenance = labels_present = 0
    columns = None
    for frame in pd.read_csv(path, chunksize=100_000, low_memory=False):
        rows += len(frame)
        columns = list(frame.columns) if columns is None else columns
        required = {'timestamp', 'session_start', 'src', 'dst', 'src_port', 'dst_port',
                    'protocol', 'source_pcap_sha256', 'labels_applied',
                    'capture_date', 'capture_member', 'flow_semantics',
                    'flow_feature_source', *PACKET_FEATURES}
        missing = required - set(frame)
        if missing:
            raise ValueError(f'{path}: missing {sorted(missing)}')
        labels_present += len({'label', 'stage', 'attack_stage', 'infiltration'} & set(frame))
        endpoints = frame.src.notna() & frame.dst.notna()
        tuple_numeric = frame[['src_port', 'dst_port', 'protocol']].apply(pd.to_numeric, errors='coerce')
        invalid_tuple += int((~endpoints | ~np.isfinite(tuple_numeric).all(axis=1)).sum())
        packet = frame[list(PACKET_FEATURES)].apply(pd.to_numeric, errors='coerce')
        invalid_packet += int((~np.isfinite(packet).all(axis=1) | ~packet.packet_features_available.eq(1)).sum())
        bad_provenance += int((frame.flow_feature_source != PROVENANCE_LABEL).sum())
        bad_provenance += int((frame.source_pcap_sha256 != expected_source_hash).sum())
        bad_provenance += int((frame.capture_date != expected_date).sum())
        bad_provenance += int((frame.capture_member != expected_member).sum())
        bad_provenance += int(~frame.labels_applied.astype(str).str.lower().eq('false').all())
        # The exporter emits valid ISO-8601 with optional fractional seconds.
        # Explicit ISO8601 parsing avoids pandas inferring one fractional format
        # for a chunk and falsely rejecting a whole-second timestamp.
        invalid_tuple += int(pd.to_datetime(frame.timestamp, format='ISO8601', errors='coerce', utc=True).isna().sum())
        invalid_tuple += int(pd.to_datetime(frame.session_start, format='ISO8601', errors='coerce', utc=True).isna().sum())
    return {'rows': rows, 'columns': columns, 'column_count': len(columns or []),
            'invalid_tuple_or_time_rows': invalid_tuple,
            'invalid_packet_rows': invalid_packet, 'bad_provenance_rows': bad_provenance,
            'label_columns_present': labels_present,
            'passed': bool(rows and not any((invalid_tuple, invalid_packet, bad_provenance, labels_present)))}


def main():
    if OUTPUT.exists() or AUDIT.exists():
        raise FileExistsError('Preserve existing R0 manifest/audit')
    records, audit_records = [], []
    for source in expected_sources():
        source_path = ROOT / source['path']
        if digest(source_path) != source['sha256']:
            raise ValueError(f'Source hash mismatch: {source_path}')
        csv_path = ROOT / 'data/real_chunk/flows_raw' / source['date'] / (source_path.stem + '.csv')
        report_path = ROOT / 'examples/real_data_validation/r0/exports' / source['date'] / (source_path.stem + '.json')
        report = json.loads(report_path.read_text(encoding='utf-8'))
        if report['status'] != 'complete_unlabeled_fallback_export':
            raise ValueError(f'Incomplete export: {report_path}')
        if (report.get('source_sha256') != source['sha256']
                or report.get('capture_date') != source['date']
                or report.get('capture_member') != source['member']
                or report.get('labels_applied') is not False
                or report.get('flow_feature_source') != PROVENANCE_LABEL
                or report.get('packet_feature_field_count') != len(PACKET_FEATURES)
                or report.get('packet_feature_fields') != list(PACKET_FEATURES)):
            raise ValueError(f'Export report provenance/contract mismatch: {report_path}')
        csv_hash = digest(csv_path)
        if csv_hash != report['output_sha256']:
            raise ValueError(f'Output hash mismatch: {csv_path}')
        detail = audit_csv(csv_path, source['sha256'], source['date'], source['member'])
        audit_records.append({'date': source['date'], 'source': source['path'],
                              'output': str(csv_path.relative_to(ROOT)), **detail})
        records.append({
            'date': source['date'], 'capture_member': source['member'],
            'source_path': source['path'], 'source_bytes': source_path.stat().st_size,
            'source_sha256': source['sha256'],
            'output_path': str(csv_path.relative_to(ROOT)), 'output_bytes': csv_path.stat().st_size,
            'output_sha256': csv_hash, 'rows': detail['rows'],
            'flow_feature_source': PROVENANCE_LABEL,
            'labels_applied': 'false',
        })
    passed = all(record['passed'] for record in audit_records)
    if not passed:
        raise ValueError('One or more R0 fallback outputs failed audit')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)
    result = {
        'passed': True, 'output_count': len(records),
        'selected_dates': sorted({record['date'] for record in records}),
        'manifest': str(OUTPUT.relative_to(ROOT)), 'manifest_sha256': digest(OUTPUT),
        'records': audit_records,
        'flow_feature_source': PROVENANCE_LABEL,
        'labels_applied': False,
        'lateral_movement_transition_included': False,
        'lateral_movement_disclosure': (
            'Real-chunk validation does not include a Lateral Movement transition. '
            'Kill-chain-diversity validation on real data covers the other represented '
            'stages only; it does not validate Lateral Movement.'
        ),
        'physical_output_schema_note': (
            'Each unlabeled R0 CSV has 42 physical columns: the fallback flow/packet '
            'fields with four label fields omitted, plus six R0 provenance fields. '
            'The mandated provenance label is preserved verbatim.'
        ),
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
