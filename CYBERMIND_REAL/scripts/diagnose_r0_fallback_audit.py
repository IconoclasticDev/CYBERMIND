"""Read-only detail for an R0 fallback audit failure."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from audit_r0_fallback_outputs import ROOT, audit_csv, digest, expected_sources


def main() -> None:
    records = []
    for source in expected_sources():
        source_path = ROOT / source['path']
        csv_path = ROOT / 'data/real_chunk/flows_raw' / source['date'] / (source_path.stem + '.csv')
        report_path = ROOT / 'examples/real_data_validation/r0/exports' / source['date'] / (source_path.stem + '.json')
        report = json.loads(report_path.read_text(encoding='utf-8'))
        detail = audit_csv(csv_path, source['sha256'], source['date'], source['member'])
        invalid_examples = []
        if detail['invalid_tuple_or_time_rows']:
            row_offset = 0
            for frame in pd.read_csv(csv_path, chunksize=100_000, low_memory=False):
                endpoints = frame.src.notna() & frame.dst.notna()
                numeric = frame[['src_port', 'dst_port', 'protocol']].apply(pd.to_numeric, errors='coerce')
                timestamp_ok = pd.to_datetime(frame.timestamp, format='ISO8601', errors='coerce', utc=True).notna()
                session_ok = pd.to_datetime(frame.session_start, format='ISO8601', errors='coerce', utc=True).notna()
                bad = ~endpoints | ~np.isfinite(numeric).all(axis=1) | ~timestamp_ok | ~session_ok
                for index in frame.index[bad]:
                    invalid_examples.append({
                        'csv_row_index': row_offset + int(index),
                        'src': None if pd.isna(frame.at[index, 'src']) else str(frame.at[index, 'src']),
                        'dst': None if pd.isna(frame.at[index, 'dst']) else str(frame.at[index, 'dst']),
                        'src_port': str(frame.at[index, 'src_port']),
                        'dst_port': str(frame.at[index, 'dst_port']),
                        'protocol': str(frame.at[index, 'protocol']),
                        'timestamp': str(frame.at[index, 'timestamp']),
                        'session_start': str(frame.at[index, 'session_start']),
                        'endpoint_valid': bool(endpoints.at[index]),
                        'numeric_tuple_valid': bool(np.isfinite(numeric.loc[index]).all()),
                        'timestamp_valid': bool(timestamp_ok.at[index]),
                        'session_start_valid': bool(session_ok.at[index]),
                    })
                row_offset += len(frame)
        records.append({
            'date': source['date'],
            'source': source['path'],
            'source_hash_matches': digest(source_path) == source['sha256'],
            'output': str(csv_path.relative_to(ROOT)),
            'output_hash_matches_report': digest(csv_path) == report.get('output_sha256'),
            'invalid_examples': invalid_examples,
            **detail,
        })
    result = {'passed': all(record['passed'] for record in records), 'records': records}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
