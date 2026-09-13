"""Apply the exact approved policy, reproduce missing weights, extend to epoch 200."""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'src'))
from cybermind.utils.checkpoint_selection import CheckpointSelection


def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))


def main():
    os.chdir(ROOT)
    os.environ.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONUTF8='1', CUDA_VISIBLE_DEVICES='',
                     TEMP=str(ROOT/'.phase3-tmp'), TMP=str(ROOT/'.phase3-tmp'))
    folder = OUT/'extended200'; folder.mkdir(parents=True, exist_ok=True)
    if (folder/'config.yaml').exists(): raise FileExistsError('Never overwrite an existing experiment.')
    original = ROOT/'examples/phase3_second_escalation/periodic100'
    cfg = yaml.safe_load((original/'config.yaml').read_text())
    cfg['train'].update(selection_metric='val_f1_stage_band', selection_f1_tolerance=.05, selection_stage_metric='stage',
                        epochs=200, early_stopping_patience=201,
                        checkpoint=str(folder/'checkpoints/combined.pt'), history_path=str(folder/'train_history.json'))
    (folder/'config.yaml').write_text(yaml.safe_dump(cfg), encoding='utf-8')
    selector = CheckpointSelection(cfg['train']); events = []
    old_history = read(original/'train_history.json')
    for row in old_history:
        changed = selector.update(row['epoch'], row['val'])
        events.append(dict(epoch=row['epoch'], validation_f1=row['val']['f1'], validation_stage_ce=row['val']['stage'],
                           selected_now=changed, state=selector.state_dict()))
    (OUT/'retrospective_selection.json').write_text(json.dumps(dict(
        policy=cfg['train']['selection_metric'], tolerance=.05, tie_break='validation stage CE',
        source_history_sha256=hashlib.sha256((original/'train_history.json').read_bytes()).hexdigest(),
        selected_epoch=selector.selected_epoch, events=events), indent=2), encoding='utf-8')
    assert selector.selected_epoch == 98
    status = dict(protocol_fixed_before_training=True, target_epoch=200, tolerance=.05,
                  historical_selected_epoch=98, commands=[], integration_gate_changed=False)
    def run(label, arguments):
        print('START', label, flush=True)
        with (folder/f'{label}.log').open('w', encoding='utf-8') as log:
            result = subprocess.run([sys.executable, *arguments], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        status['commands'].append(dict(label=label, arguments=arguments, exit_code=result.returncode))
        (folder/'status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
        if result.returncode: raise RuntimeError(f'{label} failed; inspect log')
    run('reproduce100', ['scripts/train.py', '--config', str(folder/'config.yaml'), '--device', 'cpu', '--epochs', '100'])
    spec = importlib.util.spec_from_file_location('parity', ROOT/'examples/phase2_stage_decoder/run_verification.py')
    h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
    h.compare_legacy(read(folder/'train_history.json'), old_history)
    status['all_100_epochs_reproduced_within_1e_6'] = True
    archive = folder/'reproduced100'; archive.mkdir()
    for name in ('combined.pt', 'combined_last.pt'):
        shutil.copyfile(folder/'checkpoints'/name, archive/name)
    shutil.copyfile(folder/'train_history.json', archive/'train_history.json')
    run('rollout98', ['examples/phase3_root_cause/inspect_rollouts.py', '--checkpoint', str(archive/'combined.pt'),
                      '--output', str(folder/'rollout98.json'), '--device', 'cpu'])
    run('extend200', ['scripts/train.py', '--config', str(folder/'config.yaml'), '--device', 'cpu',
                       '--resume', str(folder/'checkpoints/combined_last.pt')])
    history = read(folder/'train_history.json'); assert len(history) == 200
    h.compare_legacy(history[:100], old_history)
    assert all(math.isfinite(v) for row in history for split in ('train', 'val') for v in row[split].values() if isinstance(v, (int, float)))
    for suffix in ('', '_last'):
        run('rollout'+suffix, ['examples/phase3_root_cause/inspect_rollouts.py', '--checkpoint', str(folder/f'checkpoints/combined{suffix}.pt'),
                              '--output', str(folder/f'rollout{suffix}.json'), '--device', 'cpu'])
    status.update(execution='complete', epochs_completed=200,
                  original_rule_reviewed_epoch=read(folder/'rollout98.json')['selected_epoch'],
                  extended_selected_epoch=read(folder/'rollout.json')['selected_epoch'],
                  extended_selected_all_steps_pass=read(folder/'rollout.json')['all_steps_pass'],
                  extended_last_all_steps_pass=read(folder/'rollout_last.json')['all_steps_pass'])
    (folder/'status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in status.items() if k != 'commands'}), flush=True)


if __name__ == '__main__': main()
