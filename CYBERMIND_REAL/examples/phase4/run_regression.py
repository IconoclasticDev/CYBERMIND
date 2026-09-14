"""Fresh Phase 4 regression evidence; never rewrite historical audit fixtures."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'examples/phase4/regression'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONUTF8='1',
               PYTHONPATH=str(ROOT/'src'), TEMP=str(ROOT/'.phase3-tmp'), TMP=str(ROOT/'.phase3-tmp'))
    env.pop('CYBERMIND_TEST_EDGE_FEATURES', None)
    env.pop('CYBERMIND_TEST_CRF_STAGE', None)
    spec = importlib.util.spec_from_file_location('legacy_helpers', ROOT/'examples/phase2_stage_decoder/run_verification.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    status = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'commands': []}

    def save():
        (OUT/'verification.json').write_text(json.dumps(status, indent=2), encoding='utf-8')

    def run(name, args, cpu=False):
        cmd = [sys.executable, *args]
        print('START', name, flush=True)
        with (OUT/f'{name}.log').open('w', encoding='utf-8') as stream:
            result = subprocess.run(cmd, cwd=ROOT, env=dict(env, **({'CUDA_VISIBLE_DEVICES':''} if cpu else {})), stdout=stream, stderr=subprocess.STDOUT)
        status['commands'].append({'name':name, 'command':cmd, 'cpu':cpu, 'exit_code':result.returncode})
        save()
        assert result.returncode == 0, f'See {name}.log'
        print('PASS', name, flush=True)

    try:
        status['baseline'] = helper.verify_baseline()
        run('pytest', ['-m','pytest','tests','-q','-o','junit_family=legacy','--junitxml=examples/phase4/regression/pytest.xml'])
        cases = list(ET.parse(OUT/'pytest.xml').iter('testcase'))
        assert cases and not any(c.find(tag) is not None for c in cases for tag in ('failure','error','skipped'))
        status['tests_passed'] = len(cases)
        run('both_off', ['scripts/phase01_smoke.py','--no-use-edge-features','--no-use-crf-stage','--device','cpu','--output','examples/phase4/regression/both_off'], cpu=True)
        for name in ('eval_test.json','train_history.json'):
            helper.compare_legacy(json.loads((OUT/'both_off'/name).read_text(encoding='utf-8')), json.loads((helper.BASELINE/'integration'/name).read_text(encoding='utf-8')))
        run('legacy_eval', ['scripts/eval.py','--config','examples/smoke/baseline_before/config.yaml','--checkpoint','examples/smoke/baseline_before/baseline.pt','--output','examples/phase4/regression/legacy_eval.json'], cpu=True)
        helper.compare_legacy(json.loads((OUT/'legacy_eval.json').read_text(encoding='utf-8')), json.loads((helper.BASELINE/'eval_test.json').read_text(encoding='utf-8')))
        status['legacy_outputs_match_1e_6'] = True
        preservation = {}
        for name in ('phase3_joint','phase3_balanced_stage','phase3_root_cause','phase3_remediation','phase3_second_escalation','phase3_third_round'):
            folder = ROOT/'examples'/name
            manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
            count = 0
            for section in ('files','local_untracked_tensors_and_checkpoints'):
                for path, expected in manifest.get(section, {}).items():
                    actual = folder/path
                    assert helper.fingerprint(actual) == expected, f'Historical evidence changed: {actual}'
                    count += 1
            preservation[name] = count
        status['historical_preservation'] = preservation
        assert helper.verify_baseline() == status['baseline']
        status['passed'] = True
    except Exception as error:
        status.update(passed=False, error=str(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
