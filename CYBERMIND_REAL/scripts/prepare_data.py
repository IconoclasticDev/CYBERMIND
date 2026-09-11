#!/usr/bin/env python3
"""Chain environments chronologically, isolate splits, fit training-only features."""
from pathlib import Path
import argparse
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cybermind.data.temporal import make_sequences
from cybermind.data.dataset import save_dataset
from cybermind.data.normalization import FeatureNormalizer
from cybermind.data.pcap_extract import PACKET_FEATURES
from cybermind.data.stages import classify_stage, UNKNOWN_STAGE
from cybermind.utils.config import load_config

ROOT = Path(__file__).resolve().parents[1]
PRIMARY_SOURCE = 'CIC-IDS2018'


def read_any(path):
    return pd.read_parquet(path) if path.suffix.lower() == '.parquet' else pd.read_csv(path, low_memory=False)


def canonicalize(df, source_file):
    missing = [c for c in ['timestamp', 'src', 'dst', 'label', 'source'] if c not in df]
    if missing:
        raise ValueError(f'{source_file}: missing {missing}; rebuild with build_corpus.py')
    out = df.copy()
    out['timestamp'] = pd.to_datetime(out['timestamp'], errors='coerce', utc=True).astype('datetime64[ns, UTC]')
    if out.timestamp.isna().any():
        raise ValueError(f'{source_file}: invalid/missing timestamps; chronological chaining requires real time')
    for name in ['src', 'dst']:
        out[name] = out[name].fillna('').astype(str).str.strip()
        if out[name].str.lower().isin(['', 'nan', 'none', 'null']).any():
            raise ValueError(f'{source_file}: missing endpoint identities; use endpoint-preserving flows or PCAP')
    out['label'] = out.label.fillna('UNKNOWN').astype(str).str.strip().str.upper()
    out['infiltration'] = (out.label.map(classify_stage) != 0).astype('float32')
    stage_column = 'attack_stage' if 'attack_stage' in out else ('stage' if 'stage' in out else None)
    out['stage'] = (pd.to_numeric(out[stage_column], errors='coerce').fillna(UNKNOWN_STAGE).astype('int16')
                    if stage_column else out.label.map(classify_stage).astype('int16'))
    if not out.stage.between(0, UNKNOWN_STAGE).all():
        raise ValueError(f'{source_file}: invalid stage IDs; rebuild the canonical corpus')
    defaults = ['protocol', 'src_port', 'dst_port', 'duration', 'bytes_fwd', 'bytes_bwd',
                'packets_fwd', 'packets_bwd', 'mean_fwd_iat', 'mean_bwd_iat', 'flow_bytes_s',
                'flow_packets_s'] + list(PACKET_FEATURES)
    for name in defaults:
        out[name] = pd.to_numeric(out[name], errors='coerce').replace([np.inf, -np.inf], np.nan).fillna(0.) if name in out else 0.
    out['source_file'] = str(source_file)
    # Environment identifies one deployment, never a filename or day.
    if 'environment_id' not in out:
        out['environment_id'] = out.source
    if out.environment_id.isna().any() or out.environment_id.astype(str).str.strip().eq('').any():
        raise ValueError(f'{source_file}: empty environment_id')
    return out


def chain_environments(frames, purpose='primary'):
    data = pd.concat(frames, ignore_index=True)
    sources = set(data.source.astype(str))
    if purpose == 'primary' and sources != {PRIMARY_SOURCE}:
        raise ValueError(f'Primary training accepts only {PRIMARY_SOURCE}; found {sorted(sources)}. CTU-13/UNSW-NB15 remain held out.')
    result = {}
    for (source, environment), group in data.groupby(['source', 'environment_id'], sort=True):
        key = f'{source}::{environment}'
        result[key] = group.sort_values(['timestamp', 'source_file'], kind='stable').reset_index(drop=True)
    return result


def chronological_partitions(frame, window_seconds, stride_seconds):
    """Split events before histories; purge a full window at split boundaries."""
    seconds = frame.timestamp.astype('int64').to_numpy() / 1e9
    bins = np.floor((seconds - seconds.min()) / stride_seconds).astype('int64')
    occupied = np.unique(bins)
    if len(occupied) < 3:
        raise ValueError('Need at least three temporal bins for train/val/test')
    a = min(max(1, int(len(occupied) * .70)), len(occupied) - 2)
    b = min(max(a + 1, int(len(occupied) * .85)), len(occupied) - 1)
    first, second = seconds.min() + occupied[a] * stride_seconds, seconds.min() + occupied[b] * stride_seconds
    return {'train': frame[seconds < first - window_seconds].copy(),
            'val': frame[(seconds >= first) & (seconds < second - window_seconds)].copy(),
            'test': frame[seconds >= second].copy()}


def prepare_frames(frames, cfg, purpose='primary', normalizer=None):
    environments = chain_environments(frames, purpose)
    splits = {k: [] for k in (['train', 'val', 'test'] if purpose == 'primary' else ['test'])}
    reports = []
    if purpose == 'heldout' and normalizer is None:
        raise ValueError('Held-out evaluation requires primary training normalization constants')
    for scenario, frame in environments.items():
        partitions = chronological_partitions(frame, cfg['data']['window_seconds'], cfg['data']['stride_seconds']) if purpose == 'primary' else {'test': frame}
        for split, part in partitions.items():
            if part.empty:
                raise ValueError(f'{scenario}/{split}: no events after boundary purge; use more data')
            meta = {'source': str(frame.source.iloc[0]), 'environment_id': str(frame.environment_id.iloc[0]),
                    'source_files': list(dict.fromkeys(part.source_file)), 'split': split,
                    'endpoint_method': 'columns', 'stage_method': 'five_phase_with_unknown',
                    'packet_feature_coverage': float(part.packet_features_available.mean())}
            seqs = make_sequences(part, scenario, window_seconds=cfg['data']['window_seconds'],
                                  history=cfg['data']['history'], stride_seconds=cfg['data']['stride_seconds'],
                                  metadata=meta, normalizer=normalizer)
            splits[split].extend(seqs)
            reports.append({**meta, 'rows': len(part), 'samples': len(seqs), 'labels': sorted(part.label.unique()),
                            'start': str(part.timestamp.min()), 'end': str(part.timestamp.max())})
    if any(not samples for samples in splits.values()):
        raise ValueError('Every requested split must contain sequences; reduce smoke history or supply more data')
    if purpose == 'primary':
        normalizer = FeatureNormalizer.fit(state for sample in splits['train'] for state in sample.states)
        # Overlapping histories share graph objects; transform each only once.
        seen = set()
        for samples in splits.values():
            for sample in samples:
                sample.metadata['normalization_fingerprint'] = normalizer.fingerprint
                for state in sample.states:
                    if id(state) not in seen:
                        state.x = normalizer.transform(state.x, 'node')
                        state.edge_attr = normalizer.transform(state.edge_attr, 'edge')
                        state.metadata['normalization_fingerprint'] = normalizer.fingerprint
                        seen.add(id(state))
    return splits, normalizer, reports


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--input', default='data/intermediate/CIC-IDS2018')
    ap.add_argument('--strict', action='store_true', help='Compatibility flag; preparation always fails on invalid sources')
    ap.add_argument('--purpose', choices=['primary', 'heldout'], default='primary')
    ap.add_argument('--normalization', help='Required training normalization.json for heldout mode')
    args = ap.parse_args()
    cfg = load_config(args.config)
    raw, out = ROOT / args.input, ROOT / cfg['data']['processed_dir']
    files = sorted(list(raw.rglob('*.parquet')) + list(raw.rglob('*.csv')))
    if not files:
        raise SystemExit(f'No canonical data under {raw}. Run build_corpus.py first.')
    if args.purpose == 'heldout' and not args.normalization:
        raise SystemExit('--purpose heldout requires --normalization from primary training')
    if args.purpose == 'primary' and args.normalization:
        raise SystemExit('Primary preparation fits fresh training-only constants; omit --normalization')
    if args.purpose == 'heldout' and ((out / 'train.pt').exists() or (out / 'val.pt').exists()):
        raise SystemExit('Use a separate output directory for held-out data')
    frames = [canonicalize(read_any(f), str(f)) for f in files]
    normalizer = FeatureNormalizer.load(args.normalization) if args.normalization else None
    splits, normalizer, reports = prepare_frames(frames, cfg, args.purpose, normalizer)
    out.mkdir(parents=True, exist_ok=True)
    normalizer.save(out / 'normalization.json')
    for name, samples in splits.items():
        save_dataset(samples, out / f'{name}.pt')
        print(f'{name}: {len(samples)} sequences')
    metadata = {'purpose': args.purpose, 'primary_source': PRIMARY_SOURCE, 'reports': reports,
                'normalization_fingerprint': normalizer.fingerprint, 'split_method': 'chronological_events_with_window_purge',
                'source_files': [str(f) for f in files], 'num_sequences': sum(map(len, splits.values()))}
    (out / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
