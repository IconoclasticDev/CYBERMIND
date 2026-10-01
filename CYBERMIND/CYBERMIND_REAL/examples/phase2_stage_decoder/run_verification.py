"""Phase 2 exit evidence: real CUDA/PyG tests, frozen regression and CPU CRF smoke."""
from pathlib import Path
import datetime
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASELINE = ROOT / 'examples/smoke/baseline_before'


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')


def compare_legacy(actual, expected, path='root'):
    """Allow additive fields; every original field must still match."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and expected.keys() <= actual.keys(), path
        for key, value in expected.items():
            compare_legacy(actual[key], value, f'{path}.{key}')
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), path
        for index, (a, e) in enumerate(zip(actual, expected)):
            compare_legacy(a, e, f'{path}[{index}]')
    elif isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6), (path, actual, expected)
    else:
        assert actual == expected, (path, actual, expected)


def fingerprint(path):
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def verify_baseline():
    manifest_path = BASELINE / 'baseline_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert len(manifest['files']) == 49, 'Expected the 49 frozen Phase 0 evidence files.'
    for name, expected in manifest['files'].items():
        assert fingerprint(BASELINE / name) == expected, f'Frozen baseline changed: {name}'
    return {'verified_files': len(manifest['files']), 'manifest': fingerprint(manifest_path)}


def verify_matrix(path):
    required = {
        'test_finite_loss_gradients_and_zero_illegal_decode':
            ('emissions_gradient_norm', 'transitions_gradient_norm', 'loss', 'decoded_illegal_transition_rate'),
        'test_adversarial_independent_argmax_is_illegal_but_viterbi_is_legal':
            ('independent_argmax_rate', 'viterbi_rate'),
        'test_crf_training_gradient_and_forecast_integration':
            ('joint_loss', 'crf_loss', 'transition_gradient_norm', 'forecast_illegal_transition_rate'),
    }
    cases = list(ET.parse(path).iter('testcase'))
    matrix = []
    for name, properties_required in required.items():
        for device in ('cpu', 'cuda'):
            exact_name = f'{name}[{device}]'
            matching = [case for case in cases if case.attrib['name'] == exact_name]
            assert len(matching) == 1, f'Missing or duplicate exit case: {exact_name}'
            case = matching[0]
            assert not any(case.find(tag) is not None for tag in ('failure', 'error', 'skipped')), exact_name
            properties = {p.attrib['name']: p.attrib['value'] for p in case.findall('./properties/property')}
            assert properties.get('device') == device, exact_name
            for key in properties_required:
                assert key in properties and math.isfinite(float(properties[key])), (exact_name, key)
                if 'gradient_norm' in key:
                    assert float(properties[key]) > 0, (exact_name, key)
                if key in ('decoded_illegal_transition_rate', 'viterbi_rate', 'forecast_illegal_transition_rate'):
                    assert float(properties[key]) == 0, (exact_name, key)
            if 'independent_argmax_rate' in properties:
                assert float(properties['independent_argmax_rate']) > 0, exact_name
            matrix.append({'test': exact_name, 'status': 'passed', 'properties': properties})
    return {'all_six_passed_without_skips': True, 'cases': matrix,
            'full_suite_test_cases': len(cases),
            'full_suite_skips': sum(case.find('skipped') is not None for case in cases)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    os.chdir(ROOT)
    os.environ.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONHASHSEED='42', PYTHONUTF8='1')
    temp = ROOT / '.phase2-tmp'
    temp.mkdir(exist_ok=True)
    os.environ.update(TEMP=str(temp), TMP=str(temp))
    sys.path.insert(0, str(ROOT / 'src'))
    status = {'phase': 2, 'status': 'running', 'synthetic_only': True,
              'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'runtime': {'python': sys.version, 'executable': sys.executable}, 'commands': []}
    write('verification_status.json', status)

    def run(name, args, cpu=False):
        env = os.environ.copy()
        if cpu:
            env['CUDA_VISIBLE_DEVICES'] = ''
        command = [sys.executable, *args]
        record = {'name': name, 'command': command, 'status': 'running', 'cpu_only': cpu}
        status['commands'].append(record)
        write('verification_status.json', status)
        print('START', name, flush=True)
        started = time.monotonic()
        with (OUT / f'{name}.log').open('w', encoding='utf-8') as log:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        record.update(exit_code=result.returncode, seconds=round(time.monotonic() - started, 3),
                      status='passed' if result.returncode == 0 else 'failed')
        write('verification_status.json', status)
        assert result.returncode == 0, f'See {OUT / (name + ".log")}'
        print('PASSED', name, flush=True)

    try:
        import torch
        import yaml
        from cybermind.models import graph_encoder
        assert Path(sys.prefix).resolve() == (ROOT / '.venv').resolve(), 'Run with project .venv Python.'
        assert torch.cuda.is_available(), 'Phase 2 exit requires actual CUDA coverage.'
        assert graph_encoder.HAS_PYG, 'Phase 2 exit requires actual PyG availability.'
        torch.set_num_threads(2)
        status['runtime'].update(torch=torch.__version__, gpu=torch.cuda.get_device_name(0),
                                 cuda=torch.version.cuda, pyg_available=True)
        before = verify_baseline()
        status['baseline_before'] = before
        write('verification_status.json', status)
        run('pytest', ['-m', 'pytest', 'tests', '-q', '-o', 'junit_family=legacy',
                       '--junitxml=examples/phase2_stage_decoder/pytest.xml'])
        matrix = verify_matrix(OUT / 'pytest.xml')
        write('execution_matrix.json', matrix)
        run('legacy_checkpoint_eval', ['scripts/eval.py', '--config',
            'examples/smoke/baseline_before/config.yaml', '--checkpoint',
            'examples/smoke/baseline_before/baseline.pt', '--output',
            'examples/phase2_stage_decoder/legacy_eval.json'], cpu=True)
        compare_legacy(json.loads((OUT / 'legacy_eval.json').read_text(encoding='utf-8')),
                       json.loads((BASELINE / 'eval_test.json').read_text(encoding='utf-8')))
        status['legacy_checkpoint_eval_matches_within_1e_6'] = True

        cfg = yaml.safe_load((BASELINE / 'config.yaml').read_text(encoding='utf-8'))
        cfg['model']['use_edge_features'] = False
        cfg['loss'].update(use_crf_stage=True, crf_stage=0.5)
        cfg['train'].update(num_workers=0, epochs=1, checkpoint='phase2_crf.pt',
                            history_path='examples/phase2_stage_decoder/train_history.json')
        (OUT / 'crf_smoke.yaml').write_text(yaml.safe_dump(cfg), encoding='utf-8')
        run('crf_train', ['scripts/train.py', '--config', 'examples/phase2_stage_decoder/crf_smoke.yaml',
                          '--device', 'cpu', '--epochs', '1'], cpu=True)
        run('crf_eval', ['scripts/eval.py', '--config', 'examples/phase2_stage_decoder/crf_smoke.yaml',
                         '--checkpoint', 'checkpoints/phase2_crf.pt', '--output',
                         'examples/phase2_stage_decoder/crf_eval.json'], cpu=True)
        history = json.loads((OUT / 'train_history.json').read_text(encoding='utf-8'))
        assert len(history) == 1
        for split in ('train', 'val'):
            for key in ('loss', 'crf_stage'):
                assert math.isfinite(history[0][split][key]), (split, key)
        evaluation = json.loads((OUT / 'crf_eval.json').read_text(encoding='utf-8'))
        assert evaluation['metrics']['illegal_transition_rate'] == 0.0
        assert evaluation['metrics']['stage_transition_pairs'] > 0
        ck = torch.load(ROOT / 'checkpoints/phase2_crf.pt', map_location='cpu', weights_only=False)
        assert ck['config']['loss']['use_crf_stage'] is True
        assert ck['config']['model']['use_edge_features'] is False
        for name in ('transitions', 'allowed_transitions', 'reset_transitions'):
            assert 'stage_decoder.' + name in ck['model_state'], name
        after = verify_baseline()
        assert before == after, 'Baseline manifest or evidence changed during verification.'
        status.update(status='passed', all_six_cases_passed_without_skips=True,
                      baseline_after=after, frozen_baseline_unchanged=True,
                      crf_training_finite=True, crf_checkpoint_policy_preserved=True,
                      crf_eval_illegal_transition_rate=0.0,
                      crf_eval_transition_pairs=evaluation['metrics']['stage_transition_pairs'])
        print('PHASE 2 EXIT CHECKS PASSED', flush=True)
    except Exception as exc:
        status.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        status['finished_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write('verification_status.json', status)


if __name__ == '__main__':
    main()
