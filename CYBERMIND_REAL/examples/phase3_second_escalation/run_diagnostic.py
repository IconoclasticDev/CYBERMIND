"""Approved diagnostic #6: original inputs, fixed periodic representation, CPU."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import math
import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'src'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    os.chdir(ROOT)
    os.environ.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONUTF8='1', CUDA_VISIBLE_DEVICES='',
                     TEMP=str(ROOT/'.phase3-tmp'), TMP=str(ROOT/'.phase3-tmp'))
    folder = OUT/'periodic100'
    folder.mkdir(parents=True, exist_ok=True)
    if (folder/'config.yaml').exists():
        raise FileExistsError('Refuse to overwrite an existing diagnostic.')
    source = ROOT/'examples/phase3_root_cause/original_pipeline/processed'
    before = {p.name: digest(p) for p in source.iterdir() if p.is_file()}
    train = torch.load(source/'train.pt', weights_only=False, map_location='cpu')
    states = {(s.scenario_id, s.timestamp): s for sample in train for s in sample.states}
    states = sorted(states.values(), key=lambda s: s.timestamp)
    seconds = np.array([s.timestamp-states[0].timestamp for s in states])
    coordinate = np.array([float(s.x[0, 2]) for s in states])
    slope, intercept = np.linalg.lstsq(np.column_stack((seconds, np.ones_like(seconds))), coordinate, rcond=None)[0]
    periodic = dict(column=2, slope=float(slope), intercept=float(intercept), period=4.)
    cfg = yaml.safe_load((ROOT/'examples/phase3_root_cause/original_cuda/config.yaml').read_text())
    cfg['model']['periodic_clock'] = periodic
    cfg['train'].update(epochs=100, early_stopping_patience=101,
        checkpoint=str(folder/'checkpoints/combined.pt'), history_path=str(folder/'train_history.json'))
    (folder/'config.yaml').write_text(yaml.safe_dump(cfg), encoding='utf-8')
    status = dict(diagnostic=6, device='cpu', epochs_requested=100, representation=periodic,
                  original_input_hashes=before, original_input_width=34, derived_input_width=36,
                  integration_gate_changed=False, commands=[])
    def run(label, args):
        print('START', label, flush=True)
        with (folder/f'{label}.log').open('w', encoding='utf-8') as log:
            result = subprocess.run([sys.executable, *args], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        status['commands'].append(dict(label=label, arguments=args, exit_code=result.returncode))
        if result.returncode: raise RuntimeError(f'{label} failed; inspect log')
    try:
        run('train', ['scripts/phase3_train_measure.py', '--config', str(folder/'config.yaml'), '--device', 'cpu', '--measurement', str(folder/'memory.json')])
        history = json.loads((folder/'train_history.json').read_text())
        assert len(history) == 100
        assert all(math.isfinite(v) for row in history for split in ('train', 'val') for v in row[split].values() if isinstance(v, (int, float)))
        for suffix in ('', '_last'):
            run('rollout'+suffix, ['examples/phase3_root_cause/inspect_rollouts.py', '--checkpoint', str(folder/f'checkpoints/combined{suffix}.pt'), '--output', str(folder/f'rollout{suffix}.json'), '--device', 'cpu'])
        status.update(execution='complete', epochs_completed=100,
            selected=json.loads((folder/'rollout.json').read_text())['per_step'],
            last=json.loads((folder/'rollout_last.json').read_text())['per_step'])
        status['integration_pass'] = all(s['passed'] for s in status['selected'])
    finally:
        after = {p.name: digest(p) for p in source.iterdir() if p.is_file()}
        assert before == after
        status['original_inputs_unchanged'] = True
        (folder/'status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in status.items() if k not in ('commands','selected','last','original_input_hashes')}), flush=True)


if __name__ == '__main__':
    main()
