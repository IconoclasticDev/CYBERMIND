#!/usr/bin/env python3
"""Convert a primary corpus or a separately held-out corpus, without silent skips."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cybermind.data.adapters.unified import UnifiedAdapter

SPECS = {name: name for name in ['CIC-IDS2018', 'CIC-IDS2017', 'UNSW-NB15', 'CTU-13', 'CICIoT2023']}


def validate_source(source, purpose):
    if purpose == 'primary' and source != 'CIC-IDS2018':
        raise ValueError('Primary training is CIC-IDS2018 only. Use --purpose heldout and a separate directory for other datasets.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True, choices=SPECS)
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--chunksize', type=int, default=250000)
    ap.add_argument('--purpose', choices=['primary', 'heldout'], default='primary')
    ap.add_argument('--environment-id', help='Deployment identity shared across days; defaults to source testbed')
    args = ap.parse_args()
    validate_source(args.source, args.purpose)
    if args.chunksize <= 0:
        raise ValueError('--chunksize must be positive')
    out_dir = Path(args.output)
    previous_report = out_dir / 'adapter_report.json'
    if previous_report.exists():
        previous = json.loads(previous_report.read_text(encoding='utf-8'))
        if previous.get('source') != args.source or previous.get('purpose', 'primary') != args.purpose:
            raise ValueError('Output contains a different corpus/purpose; use a separate output directory')
    source_path = Path(args.input)
    files = sorted(source_path.rglob('*.csv')) if source_path.is_dir() else [source_path]
    if not files or any(not path.is_file() for path in files):
        raise ValueError('No source CSV files found')
    # Preserve relative paths: repeated day/chunk basenames cannot overwrite files.
    base = source_path if source_path.is_dir() else source_path.parent
    adapter = UnifiedAdapter(args.source)
    reports, written = [], []
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in files:
        out, report = adapter.convert(path, chunksize=args.chunksize)
        if out.empty:
            raise ValueError(f'{path}: conversion returned no events')
        out['source_file'] = str(path.relative_to(base))
        if 'environment_id' not in out:
            out['environment_id'] = args.environment_id or args.source
        elif args.environment_id:
            out['environment_id'] = args.environment_id
        destination = out_dir / path.relative_to(base).with_suffix('.parquet')
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            import pyarrow  # noqa: F401
        except ImportError:
            destination = destination.with_suffix('.csv')
            out.to_csv(destination, index=False)
        else:
            out.to_parquet(destination, index=False)
        written.append(str(destination))
        reports.append(report.__dict__)
        print(f'OK {path.name}: {len(out):,} rows -> {destination}')
    previous_report.write_text(json.dumps({'source': args.source, 'purpose': args.purpose,
        'environment_id': args.environment_id or args.source, 'files': written,
        'reports': reports, 'input_files': [str(path) for path in files],
        'selection': 'all supplied files and attack labels; no row sampling'}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
