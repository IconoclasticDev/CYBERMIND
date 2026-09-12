"""Final-plan Phase 1 exit checks. Synthetic only; requires real CUDA + PyG."""
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


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')


def compare_json(actual, expected):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            compare_json(actual[key], expected[key])
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for a, e in zip(actual, expected):
            compare_json(a, e)
    elif isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6), (actual, expected)
    else:
        assert actual == expected, (actual, expected)


def main():
    os.chdir(ROOT)
    os.environ.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONHASHSEED='42', PYTHONUTF8='1')
    temp = ROOT / '.phase1-tmp'
    temp.mkdir(exist_ok=True)
    os.environ.update(TEMP=str(temp), TMP=str(temp))
    sys.path.insert(0, str(ROOT / 'src'))
    sys.path.insert(0, str(ROOT / 'scripts'))
    import torch
    import yaml
    import pandas as pd
    from cybermind.models import graph_encoder as current
    from cybermind.data.graph_builder import build_graph_state, EDGE_FEATURE_NAMES
    from prepare_data import canonicalize
    torch.set_num_threads(2)
    assert torch.cuda.is_available(), 'Phase 1 cannot exit without actual CUDA coverage.'
    assert current.HAS_PYG, 'Phase 1 cannot exit without actual PyG coverage.'
    status = {'phase': 1, 'synthetic_only': True, 'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'runtime': {'python': sys.version, 'executable': sys.executable, 'torch': torch.__version__,
                          'gpu': torch.cuda.get_device_name(0)}, 'commands': []}
    write('verification_status.json', status)

    def run(name, args, *, cpu_eval=False):
        env = os.environ.copy()
        if cpu_eval:
            env['CUDA_VISIBLE_DEVICES'] = ''
        command = [sys.executable, *args]
        record = {'name': name, 'command': command, 'status': 'running'}
        status['commands'].append(record)
        write('verification_status.json', status)
        print('START', name, flush=True)
        start = time.monotonic()
        with (OUT / f'{name}.log').open('w', encoding='utf-8') as log:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        record.update(exit_code=result.returncode, seconds=round(time.monotonic()-start, 3),
                      status='passed' if result.returncode == 0 else 'failed')
        write('verification_status.json', status)
        print(record['status'].upper(), name, flush=True)
        assert result.returncode == 0, f'See {OUT / (name + ".log")}'

    canonical = ROOT / 'examples/smoke/baseline_before/integration/canonical/z_earlier.parquet'
    frame = canonicalize(pd.read_parquet(canonical), str(canonical))
    state = build_graph_state(frame, 'phase1-schema-probe', {'synthetic_only': True})
    assert state.edge_attr.dtype == torch.float32
    assert state.edge_attr.shape == (state.edge_index.size(1), len(EDGE_FEATURE_NAMES))
    assert len(EDGE_FEATURE_NAMES) == 27 and torch.isfinite(state.edge_attr).all()
    write('edge_schema.json', {'source': str(canonical.relative_to(ROOT)), 'graph_builder_modified': False,
                              'edge_shape': list(state.edge_attr.shape), 'edge_dtype': str(state.edge_attr.dtype),
                              'feature_names': EDGE_FEATURE_NAMES})

    # This is the actual pre-Phase-1 implementation, not a second new-model instance.
    spec = importlib.util.spec_from_file_location('phase0_graph_encoder', OUT / 'legacy_graph_encoder.py')
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    original_backend = current.HAS_PYG
    compatibility = []
    for device in ('cpu', 'cuda'):
        for backend in ('pyg', 'fallback'):
            current.HAS_PYG = legacy.HAS_PYG = backend == 'pyg'
            torch.manual_seed(73)
            old = legacy.GATv2GraphEncoder(14, 8, 8, heads=2, dropout=0.).to(device).eval()
            torch.manual_seed(73)
            new = current.GATv2GraphEncoder(14, 8, 8, heads=2, dropout=0.,
                edge_attr_dim=27, use_edge_features=False).to(device).eval()
            assert old.state_dict().keys() == new.state_dict().keys()
            assert all(torch.equal(value, new.state_dict()[key]) for key, value in old.state_dict().items())
            x = torch.randn(3, 14, device=device)
            edges = torch.tensor([[0, 2, 1, 2, 0, 1], [1, 1, 0, 0, 2, 2]], device=device)
            attrs = torch.randn(6, 27, device=device)
            with torch.no_grad():
                a, b = old(x, edges), new(x, edges, attrs)
            # CUDA scatter reductions can vary at rounding precision between calls.
            torch.testing.assert_close(a, b, rtol=1e-6, atol=1e-6)
            compatibility.append({'device': device, 'backend': backend, 'state_keys_identical': True,
                                  'initial_weights_identical': True, 'outputs_bitwise_equal': torch.equal(a, b),
                                  'output_max_abs_difference': (a-b).abs().max().item(), 'atol': 1e-6, 'rtol': 1e-6})
    current.HAS_PYG = original_backend
    write('legacy_compatibility.json', {'source_commit': '1d91b27', 'cases': compatibility})

    run('pytest', ['-m', 'pytest', 'tests', '-q', '-o', 'junit_family=legacy',
                  '--junitxml=examples/phase1_edge_attention/pytest.xml'])
    test_xml = ET.parse(OUT / 'pytest.xml')
    cases = [t for t in test_xml.iter('testcase') if 'test_edge_attention_execution_matrix' in t.attrib['name']]
    assert len(cases) == 8
    matrix = []
    for case in cases:
        assert not any(case.find(tag) is not None for tag in ('failure', 'error', 'skipped'))
        properties = {p.attrib['name']: p.attrib['value'] for p in case.findall('./properties/property')}
        matrix.append({'test': case.attrib['name'], 'status': 'passed', **properties})
    write('execution_matrix.json', {'all_eight_passed_without_skips': True, 'cases': matrix})

    run('legacy_checkpoint_eval', ['scripts/eval.py', '--config', 'examples/smoke/baseline_before/config.yaml',
        '--checkpoint', 'examples/smoke/baseline_before/baseline.pt',
        '--output', 'examples/phase1_edge_attention/legacy_eval.json'], cpu_eval=True)
    compare_json(json.loads((OUT / 'legacy_eval.json').read_text()),
                 json.loads((ROOT / 'examples/smoke/baseline_before/eval_test.json').read_text()))

    cfg = yaml.safe_load((ROOT / 'examples/smoke/baseline_before/config.yaml').read_text())
    cfg['model']['use_edge_features'] = True
    # Width intentionally omitted: training must infer seven columns from this
    # older synthetic fixture and evaluation must recover it from the checkpoint.
    cfg['model'].pop('edge_attr_dim', None)
    cfg['train'].update(num_workers=0, checkpoint='phase1_edges.pt', epochs=1,
                        history_path='examples/phase1_edge_attention/train_history.json')
    (OUT / 'enabled_smoke.yaml').write_text(yaml.safe_dump(cfg), encoding='utf-8')
    run('enabled_train', ['scripts/train.py', '--config', 'examples/phase1_edge_attention/enabled_smoke.yaml',
                         '--device', 'cpu', '--epochs', '1'])
    run('enabled_eval', ['scripts/eval.py', '--config', 'examples/phase1_edge_attention/enabled_smoke.yaml',
                        '--checkpoint', 'checkpoints/phase1_edges.pt',
                        '--output', 'examples/phase1_edge_attention/enabled_eval.json'], cpu_eval=True)
    ck = torch.load(ROOT / 'checkpoints/phase1_edges.pt', map_location='cpu', weights_only=False)
    assert ck['config']['model']['use_edge_features'] is True
    assert ck['config']['model']['edge_attr_dim'] == 7
    history = json.loads((OUT / 'train_history.json').read_text())
    assert len(history) == 1 and math.isfinite(history[0]['train']['loss'])
    status.update(status='passed', all_eight_cases_passed=True, edge_schema_width=27,
                  legacy_encoder_matches_within_tolerance=True, legacy_checkpoint_eval_matches=True,
                  enabled_checkpoint_inferred_width=7, enabled_training_finite=True,
                  finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write('verification_status.json', status)
    print('PHASE 1 EXIT CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
