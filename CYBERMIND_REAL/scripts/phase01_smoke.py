#!/usr/bin/env python3
"""Synthetic integration check ONLY; never downloads data or launches GB10 training."""
from pathlib import Path
import argparse
from collections import Counter
import json
import os
import subprocess
import sys
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.data.pcap_extract import PACKET_FEATURES


def annotate_fixture_resets(processed):
    """Declare fixture campaign boundaries from its clock, never stage labels."""
    import torch
    origin = pd.Timestamp('2018-02-14', tz='UTC').timestamp()
    counts = {}
    for split in ('train', 'val', 'test'):
        path = processed / f'{split}.pt'
        samples = torch.load(path, map_location='cpu', weights_only=False)
        seen, declared = set(), 0
        for sample in samples:
            for state in sample.states:
                if id(state) in seen:
                    continue
                seen.add(id(state))
                second = round(float(state.metadata['window_start']) - origin)
                reset = second % 4 == 1
                state.metadata['campaign_reset'] = reset
                state.metadata['campaign_reset_source'] = 'synthetic_fixture_clock_modulo_4'
                declared += int(reset)
        torch.save(samples, path)
        counts[split] = {'unique_states': len(seen), 'declared_reset_states': declared}
    return {'rule': 'Each scan at second % 4 == 0 is an independent synthetic campaign; destination second % 4 == 1 resets it.',
            'source': 'fixture clock; no stage labels or predictions used',
            'tensors_features_and_labels_changed': False, 'splits': counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--use-edge-features', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('--use-crf-stage', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('--output', default='examples/phase01_integration')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    frozen = (ROOT / 'examples/smoke/baseline_before').resolve()
    if output == frozen or frozen in output.parents:
        raise ValueError('The frozen Phase 0 baseline cannot be an output directory')
    raw = output / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    rows = []
    for second in range(180):
        for flow in range(2):
            row = dict(timestamp=str(pd.Timestamp('2018-02-14') + pd.Timedelta(seconds=second)),
                       src='10.0.0.1', dst='10.0.0.2', protocol=6, src_port=1000,
                       dst_port=80, bytes_fwd=100 + second, packets_fwd=1,
                       environment_id='SYNTHETIC_FIXTURE_ONLY',
                       label='PORTSCAN' if second % 4 == 0 and flow == 1 else 'BENIGN')
            row.update({name: 0.0 for name in PACKET_FEATURES})
            row.update(ttl_mean=64., tcp_window_mean=1024., packet_features_available=1.)
            rows.append(row)
    # Deliberately reverse filename order relative to chronology.
    pd.DataFrame(rows[:180]).to_csv(raw / 'z_earlier.csv', index=False)
    pd.DataFrame(rows[180:]).to_csv(raw / 'a_later.csv', index=False)
    config = yaml.safe_load((ROOT / 'configs/phase01_smoke.yaml').read_text())
    config['data'].update(processed_dir=str(output / 'processed'),
                          window_seconds=1, stride_seconds=1, history=3,
                          require_normalization=True, require_packet_features=True)
    legacy_default = (output == (ROOT / 'examples/phase01_integration').resolve()
                      and not args.use_edge_features and not args.use_crf_stage and args.device == 'cpu')
    checkpoint = (ROOT / 'checkpoints/phase01_integration.pt' if legacy_default
                  else output / 'checkpoints' / f'{output.name}.pt')
    config['model']['use_edge_features'] = args.use_edge_features
    config['loss']['use_crf_stage'] = args.use_crf_stage
    config['loss']['crf_stage'] = config['loss']['stage']
    config['train'].update(checkpoint=str(checkpoint),
                           history_path=str(output / 'train_history.json'),
                           batch_size=16)
    config_path = output / 'config.yaml'
    config_path.write_text(yaml.safe_dump(config), encoding='utf-8')
    commands = [
        ['scripts/build_corpus.py', '--source', 'CIC-IDS2018', '--input', str(raw),
         '--output', str(output / 'canonical')],
        ['scripts/prepare_data.py', '--config', str(config_path), '--input', str(output / 'canonical'), '--strict'],
        ['scripts/phase3_train_measure.py', '--config', str(config_path), '--device', args.device,
         '--measurement', str(output / 'train_memory.json')],
        ['scripts/eval.py', '--config', str(config_path), '--checkpoint', str(checkpoint),
         '--output', str(output / 'eval_test.json')],
    ]
    environment = os.environ.copy()
    if args.device == 'cpu':
        environment['CUDA_VISIBLE_DEVICES'] = ''
    reset_annotation = None
    for index, command in enumerate(commands):
        with (output / f'step_{index + 1}.log').open('w', encoding='utf-8') as log:
            subprocess.run([sys.executable, *command], cwd=ROOT, env=environment,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        print('PASS', command[0], flush=True)
        if index == 1 and args.use_crf_stage:
            reset_annotation = annotate_fixture_resets(output / 'processed')
    report = json.loads((output / 'eval_test.json').read_text())
    assert report['per_sample'] and all(row['explanation']['feature_occlusion'] for row in report['per_sample'])
    stages = [stage for row in report['per_sample'] for stage in row['decoded_stages']]
    risks = [row['predicted_future_risk'] for row in report['per_sample']]
    histogram = dict(sorted(Counter(stages).items()))
    memory = json.loads((output / 'train_memory.json').read_text())
    (output / 'verification.json').write_text(json.dumps({
        'synthetic_only': True, 'real_training_performed': False,
        'steps_passed': len(commands), 'evaluated_samples': len(report['per_sample']),
        'automatic_explanations': True,
        'device': args.device, 'use_edge_features': args.use_edge_features,
        'use_crf_stage': args.use_crf_stage, 'checkpoint': str(checkpoint),
        'campaign_reset_annotation': reset_annotation,
        'stage_diversity': {'decoded_histogram': histogram, 'unique_stages': len(histogram),
                            'unknown_fraction': stages.count(6) / len(stages),
                            'single_stage_collapse': len(histogram) == 1},
        'risk_diversity': {'minimum': min(risks), 'maximum': max(risks),
                           'spread': max(risks) - min(risks)},
        'train_memory': memory,
        'warning': 'CIC-IDS2018 is a fixture routing value. These generated rows are NOT real CIC data or accuracy evidence.'
    }, indent=2), encoding='utf-8')
    print('Synthetic integration executed; inspect verification.json for diversity and memory gates.')


if __name__ == '__main__':
    main()
