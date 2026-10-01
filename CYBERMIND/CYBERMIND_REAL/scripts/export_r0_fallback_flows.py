"""Export every frozen R0 source capture without applying labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from cybermind.data.real_chunk_export import export_capture


def sources_from_plan(only=None):
    plan = json.loads((ROOT / 'examples/real_data_validation/r0/capture_scope_frozen.json').read_text(encoding='utf-8'))
    feb = json.loads((ROOT / plan['feb14_evidence']).read_text(encoding='utf-8'))
    sources = [{
        'date': '2018-02-14', 'source': plan['feb14_input'],
        'member': 'reviewed complete-record derivative of pcap/UCAP172.31.69.25',
        'sha256': feb['derivative_sha256'],
    }]
    for record in plan['additional_members']:
        if only and Path(record['target']).name != only:
            continue
        evidence_path = (ROOT / record['target']).with_suffix('.acquisition.json')
        evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
        sources.append({
            'date': record['date'], 'source': record['target'],
            'member': record['member']['name'], 'sha256': evidence['target_sha256'],
        })
    return sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', help='Export only one source filename, for a bounded retry')
    parser.add_argument('--skip-complete', action='store_true', help='Skip only outputs with a matching complete report')
    args = parser.parse_args()
    results = []
    for source in sources_from_plan(args.only):
        path = ROOT / source['source']
        if args.only and path.name != args.only:
            continue
        output = ROOT / 'data/real_chunk/flows_raw' / source['date'] / (path.stem + '.csv')
        report = ROOT / 'examples/real_data_validation/r0/exports' / source['date'] / (path.stem + '.json')
        if args.skip_complete and output.exists() and report.exists():
            existing = json.loads(report.read_text(encoding='utf-8'))
            if (existing.get('status') == 'complete_unlabeled_fallback_export'
                    and existing.get('source_sha256') == source['sha256']):
                print(f'SKIP verified complete export: {output}', flush=True)
                continue
            raise ValueError(f'Existing output is not a verified match: {output}')
        result = export_capture(path, output, report, capture_date=source['date'],
                                capture_member=source['member'], expected_sha256=source['sha256'])
        results.append(result)
        print(json.dumps(result, indent=2), flush=True)
    if not results and not args.skip_complete:
        raise ValueError('No source matched the requested export')


if __name__ == '__main__':
    main()
