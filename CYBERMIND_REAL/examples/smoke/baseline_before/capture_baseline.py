"""Reproduce final-plan Phase 0 only; no downloads or model modifications.

Run with the project's CUDA-capable .venv Python from the project directory.
Historical integration outputs are backed up and restored after their new results
are copied here. All training data used by this helper is explicitly synthetic.
"""
from pathlib import Path
import datetime
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LOGS = OUT / 'logs'


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def finite_numbers(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f'Nonfinite baseline value: {value}')
    if isinstance(value, dict):
        for item in value.values():
            finite_numbers(item)
    if isinstance(value, list):
        for item in value:
            finite_numbers(item)


def main():
    os.chdir(ROOT)
    LOGS.mkdir(parents=True, exist_ok=True)
    # Keep CPU arithmetic settings explicit and prevent worker oversubscription.
    os.environ.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONHASHSEED='42', PYTHONUTF8='1')
    temp = ROOT / '.phase0-tmp'
    temp.mkdir(exist_ok=True)
    os.environ.update(TEMP=str(temp), TMP=str(temp))
    status_path = OUT / 'execution_status.json'
    status = json.loads(status_path.read_text()) if status_path.exists() else {
        'started_at_utc': stamp(), 'synthetic_only': True, 'phase': 0, 'steps': []}
    if status.get('status') == 'passed':
        print('Baseline already complete and frozen. Use a separate directory for subsequent phases.', flush=True)
        return
    import yaml
    cfg = yaml.safe_load((ROOT / 'configs/smoke.yaml').read_text())
    live_checkpoint = ROOT / 'checkpoints' / cfg['train']['checkpoint']
    live_history = ROOT / cfg['train']['history_path']

    def run(name, args, *, extra_env=None):
        if any(s['name'] == name and s['status'] == 'passed' for s in status['steps']):
            print('ALREADY PASSED', name, flush=True)
            return
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        rec = {'name': name, 'command': [sys.executable, *args], 'started_at_utc': stamp(), 'status': 'running'}
        status['steps'].append(rec)
        dump(OUT / 'execution_status.json', status)
        print('START', name, flush=True)
        began = time.monotonic()
        log_path = LOGS / f'{name}.log'
        if log_path.exists():
            suffix = sum(s['name'] == name for s in status['steps']) - 1
            shutil.copy2(log_path, LOGS / f'{name}.previous_attempt_{suffix}.log')
        with log_path.open('w', encoding='utf-8') as log:
            result = subprocess.run(rec['command'], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        rec.update(exit_code=result.returncode, elapsed_seconds=round(time.monotonic()-began, 3),
                   status='passed' if result.returncode == 0 else 'failed', finished_at_utc=stamp())
        dump(OUT / 'execution_status.json', status)
        print(rec['status'].upper(), name, flush=True)
        if result.returncode:
            raise RuntimeError(f'{name} failed; see {LOGS / (name + ".log")}')

    run('inspect_env', ['scripts/inspect_env.py'])
    run('hardware_bf16', ['-c', "import json,os,platform,torch,psutil; from pathlib import Path; "
        "assert torch.cuda.is_available(), 'CUDA unavailable'; "
        "assert torch.cuda.is_bf16_supported(), 'bf16 unavailable'; "
        "torch.manual_seed(42); x=torch.randn(64,64,device='cuda',dtype=torch.bfloat16,requires_grad=True); "
        "loss=(x@x.T).float().square().mean(); loss.backward(); torch.cuda.synchronize(); "
        "assert torch.isfinite(loss) and torch.isfinite(x.grad).all() and x.grad.norm()>0; "
        "d=dict(python=platform.python_version(),torch=torch.__version__,cuda_runtime=torch.version.cuda,"
        "gpu=torch.cuda.get_device_name(0),compute_capability=torch.cuda.get_device_capability(0),"
        "vram_bytes=torch.cuda.get_device_properties(0).total_memory,ram_bytes=psutil.virtual_memory().total,"
        "available_ram_bytes=psutil.virtual_memory().available,logical_cpus=os.cpu_count(),"
        "bf16_supported=torch.cuda.is_bf16_supported(),bf16_loss=loss.item(),bf16_gradient_norm=x.grad.float().norm().item()); "
        "Path('examples/smoke/baseline_before/hardware.json').write_text(json.dumps(d,indent=2)); print(json.dumps(d,indent=2))"])
    with (LOGS / 'nvidia_smi.log').open('w', encoding='utf-8') as log:
        subprocess.run(['nvidia-smi'], stdout=log, stderr=subprocess.STDOUT, check=True)
    run('pytest_original_cuda_environment', ['-m', 'pytest', 'tests', '-q'])

    # Preserve historical artifacts; compare new baseline only against this run.
    originals = OUT / 'historical_artifacts'
    integration = ROOT / 'examples/phase01_integration'
    if not (originals / 'integration').exists():
        shutil.copytree(integration, originals / 'integration')
    originals.joinpath('checkpoints').mkdir(parents=True, exist_ok=True)
    checkpoint_backups = []
    for name in ('phase01_integration.pt', 'phase01_integration_last.pt'):
        old = ROOT / 'checkpoints' / name
        if old.exists():
            if not (originals / 'checkpoints' / name).exists():
                shutil.copy2(old, originals / 'checkpoints' / name)
            checkpoint_backups.append(name)
    try:
        integration_already_passed = any(s['name'] == 'phase01_smoke_original' and s['status'] == 'passed' for s in status['steps'])
        run('phase01_smoke_original', ['scripts/phase01_smoke.py'])
        if not (OUT / 'integration').exists():
            shutil.copytree(integration, OUT / 'integration')
        if not integration_already_passed:
            for name in ('phase01_integration.pt', 'phase01_integration_last.pt'):
                shutil.copy2(ROOT / 'checkpoints' / name, OUT / 'integration' / name)
    finally:
        shutil.copytree(originals / 'integration', integration, dirs_exist_ok=True)
        for name in checkpoint_backups:
            shutil.copy2(originals / 'checkpoints' / name, ROOT / 'checkpoints' / name)

    # Existing generator is unseeded; seed before executing it without editing it.
    run('generate_seeded_synthetic', ['-c', "import sys,runpy,torch; torch.manual_seed(42); "
        "sys.argv=['scripts/make_synthetic.py','--out','examples/smoke/baseline_before/processed']; "
        "runpy.run_path('scripts/make_synthetic.py',run_name='__main__')"])
    shutil.copy2(ROOT / 'configs/smoke.yaml', OUT / 'config.yaml')
    run('train_smoke_cpu', ['scripts/train.py', '--config', 'configs/smoke.yaml', '--device', 'cpu', '--epochs', '2'])
    if live_history.resolve() != (OUT / 'train_history.json').resolve():
        shutil.copy2(live_history, OUT / 'train_history.json')
    # eval.py auto-selects CUDA; hide it here to keep the regression reference on CPU.
    run('eval_smoke_cpu', ['scripts/eval.py', '--config', 'configs/smoke.yaml', '--checkpoint', str(live_checkpoint.relative_to(ROOT)),
        '--output', 'examples/smoke/baseline_before/eval_test.json'], extra_env={'CUDA_VISIBLE_DEVICES': ''})
    shutil.copy2(live_checkpoint, OUT / 'baseline.pt')
    shutil.copy2(live_checkpoint.with_name(live_checkpoint.stem + '_last.pt'), OUT / 'baseline_last.pt')
    history = json.loads((OUT / 'train_history.json').read_text())
    report = json.loads((OUT / 'eval_test.json').read_text())
    finite_numbers(history)
    finite_numbers(report)
    assert len(history) == 2 and all(math.isfinite(r['train']['loss']) for r in history)
    assert report['per_sample']
    status.update(status='passed', finished_at_utc=stamp())
    dump(OUT / 'execution_status.json', status)
    hashes = {}
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and not any(p in path.parts for p in ('historical_artifacts', '__pycache__')) and path.name != 'baseline_manifest.json':
            with path.open('rb') as stream:
                hashes[str(path.relative_to(OUT))] = {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}
    dump(OUT / 'baseline_manifest.json', {'created_at_utc': stamp(), 'synthetic_only': True,
        'cpu_regression_reference': True, 'seed': 42, 'num_workers': 8,
        'memory_recheck': 'User freed RAM; 5.57 GiB available before resuming with eight workers.',
        'arithmetic_environment': {'OMP_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2'},
        'regression_note': 'Reuse saved tensors, configuration, runtime and arithmetic settings. Historical smoke metrics are not this reference.',
        'files': hashes})
    print('PHASE 0 BASELINE CAPTURE COMPLETE', flush=True)


if __name__ == '__main__':
    main()
