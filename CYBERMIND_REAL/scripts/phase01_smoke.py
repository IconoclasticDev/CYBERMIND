#!/usr/bin/env python3
"""Synthetic integration check ONLY; never downloads data or launches GB10 training."""
from pathlib import Path
import json
import subprocess
import sys
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.data.pcap_extract import PACKET_FEATURES


def main():
    output = ROOT / 'examples/phase01_integration'
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
    config['data'].update(processed_dir='examples/phase01_integration/processed',
                          window_seconds=1, stride_seconds=1, history=3,
                          require_normalization=True, require_packet_features=True)
    config['train'].update(checkpoint='phase01_integration.pt',
                           history_path='examples/phase01_integration/train_history.json',
                           batch_size=16)
    config_path = output / 'config.yaml'
    config_path.write_text(yaml.safe_dump(config), encoding='utf-8')
    commands = [
        ['scripts/build_corpus.py', '--source', 'CIC-IDS2018', '--input', str(raw),
         '--output', str(output / 'canonical')],
        ['scripts/prepare_data.py', '--config', str(config_path), '--input', str(output / 'canonical'), '--strict'],
        ['scripts/train.py', '--config', str(config_path), '--device', 'cpu'],
        ['scripts/eval.py', '--config', str(config_path), '--checkpoint', 'checkpoints/phase01_integration.pt',
         '--output', str(output / 'eval_test.json')],
    ]
    for index, command in enumerate(commands):
        with (output / f'step_{index + 1}.log').open('w', encoding='utf-8') as log:
            subprocess.run([sys.executable, *command], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        print('PASS', command[0], flush=True)
    report = json.loads((output / 'eval_test.json').read_text())
    assert report['per_sample'] and all(row['explanation']['feature_occlusion'] for row in report['per_sample'])
    (output / 'verification.json').write_text(json.dumps({
        'synthetic_only': True, 'real_training_performed': False,
        'steps_passed': len(commands), 'evaluated_samples': len(report['per_sample']),
        'automatic_explanations': True,
        'warning': 'CIC-IDS2018 is a fixture routing value. These generated rows are NOT real CIC data or accuracy evidence.'
    }, indent=2), encoding='utf-8')
    print('Synthetic integration passed; Phase 2 was not started.')


if __name__ == '__main__':
    main()
