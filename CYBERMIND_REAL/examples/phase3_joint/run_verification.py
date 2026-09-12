"""Run the final-plan Phase 3 matrix; synthetic data only, isolated outputs."""
from pathlib import Path
import datetime
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
spec = importlib.util.spec_from_file_location('phase2_helpers', ROOT / 'examples/phase2_stage_decoder/run_verification.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def main():
    os.chdir(ROOT)
    os.environ.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONHASHSEED='42', PYTHONUTF8='1')
    temp = ROOT / '.phase3-tmp'
    temp.mkdir(exist_ok=True)
    os.environ.update(TEMP=str(temp), TMP=str(temp))
    import torch
    assert torch.cuda.is_available(), 'Actual laptop CUDA required.'
    status = dict(phase=3, status='running', synthetic_only=True, commands=[],
                  started_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  runtime=dict(python=sys.version, torch=torch.__version__,
                               gpu=torch.cuda.get_device_name(), vram_bytes=torch.cuda.get_device_properties(0).total_memory))

    def run(name, args, cpu=False, extra_env=None):
        env = os.environ.copy()
        if cpu:
            env['CUDA_VISIBLE_DEVICES'] = ''
        env.update(extra_env or {})
        command = [sys.executable, *args]
        rec = dict(name=name, command=command, cpu_only=cpu, environment=extra_env or {}, status='running')
        status['commands'].append(rec)
        write('verification_status.json', status)
        print('START', name, flush=True)
        started = time.monotonic()
        with (OUT / f'{name}.log').open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
        rec.update(exit_code=result.returncode, seconds=round(time.monotonic()-started, 3),
                   status='passed' if result.returncode == 0 else 'failed')
        write('verification_status.json', status)
        assert result.returncode == 0, f'See {OUT / (name + ".log")}'
        print('PASS', name, flush=True)

    try:
        before = helpers.verify_baseline()
        status['baseline_before'] = before
        matrix = []
        for name, edge, crf in [('baseline', False, False), ('edge_only', True, False),
                                ('crf_only', False, True), ('combined', True, True)]:
            run(f'pytest_{name}', ['-m', 'pytest', 'tests', '-q', '-o', 'junit_family=legacy',
                 f'--junitxml=examples/phase3_joint/pytest_{name}.xml'],
                extra_env={'CYBERMIND_TEST_EDGE_FEATURES': str(int(edge)), 'CYBERMIND_TEST_CRF_STAGE': str(int(crf))})
            cases = list(ET.parse(OUT / f'pytest_{name}.xml').iter('testcase'))
            assert cases and not any(c.find(tag) is not None for c in cases for tag in ('failure','error','skipped'))
            flags = ['--use-edge-features' if edge else '--no-use-edge-features',
                     '--use-crf-stage' if crf else '--no-use-crf-stage']
            run(f'integration_{name}', ['scripts/phase01_smoke.py', *flags, '--device', 'cpu',
                '--output', f'examples/phase3_joint/{name}'], cpu=True)
            report = json.loads((OUT / name / 'verification.json').read_text(encoding='utf-8'))
            history = json.loads((OUT / name / 'train_history.json').read_text(encoding='utf-8'))
            assert len(history) == 2
            for epoch in history:
                assert all(math.isfinite(v) for split in ('train','val') for v in epoch[split].values() if isinstance(v,(int,float)))
            matrix.append(dict(name=name, use_edge_features=edge, use_crf_stage=crf,
                               tests_passed=len(cases), skipped=0, integration=report))
            write('execution_matrix.json', matrix)
        # Fresh both-off pipeline regression, including per-sample outputs and history.
        for filename in ('eval_test.json', 'train_history.json'):
            helpers.compare_legacy(json.loads((OUT / 'baseline' / filename).read_text(encoding='utf-8')),
                                   json.loads((helpers.BASELINE / 'integration' / filename).read_text(encoding='utf-8')))
        status['fresh_both_off_integration_matches_within_1e_6'] = True
        run('legacy_checkpoint_eval', ['scripts/eval.py', '--config', 'examples/smoke/baseline_before/config.yaml',
            '--checkpoint', 'examples/smoke/baseline_before/baseline.pt', '--output', 'examples/phase3_joint/legacy_eval.json'], cpu=True)
        helpers.compare_legacy(json.loads((OUT / 'legacy_eval.json').read_text(encoding='utf-8')),
                               json.loads((helpers.BASELINE / 'eval_test.json').read_text(encoding='utf-8')))
        status['frozen_checkpoint_matches_within_1e_6'] = True
        run('integration_combined_cuda', ['scripts/phase01_smoke.py', '--use-edge-features', '--use-crf-stage',
            '--device', 'cuda', '--output', 'examples/phase3_joint/combined_cuda'])
        status['combined_cuda'] = json.loads((OUT / 'combined_cuda/verification.json').read_text(encoding='utf-8'))
        after = helpers.verify_baseline()
        assert before == after
        status.update(status='checks_completed_pending_audit', baseline_after=after, frozen_baseline_unchanged=True)
    except Exception as exc:
        status.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        status['finished_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write('verification_status.json', status)


if __name__ == '__main__':
    main()
