"""Exercise launcher orchestration without downloads, training, or GPU access."""
import importlib.util
from pathlib import Path
import sys
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def launcher(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('launcher_under_test', ROOT / 'scripts/launch_training.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    (tmp_path / 'configs').mkdir()
    (tmp_path / 'configs/gb10_full.yaml').write_text(yaml.safe_dump({
        'data': {'processed_dir': 'data/processed_gb10'},
        'train': {'checkpoint': 'best_gb10.pt'},
    }))
    return module


def test_default_routes_preparation_baselines_and_manifest(tmp_path, monkeypatch):
    module = launcher(tmp_path, monkeypatch)
    events = []
    monkeypatch.setattr(sys, 'argv', ['launch_training.py', '--no-download-cic2018', '--epochs', '1'])
    monkeypatch.setattr(module, 'ensure_data', lambda *a, **kw: events.append(('data', kw)))
    monkeypatch.setattr(module, 'normalize', lambda *a: None)
    def fake_run(cmd, **kwargs):
        events.append(cmd)
        if 'scripts/prepare_data.py' in cmd:
            for name in ('train.pt', 'val.pt', 'test.pt'):
                (tmp_path / 'data/processed_gb10' / name).write_bytes(b'fixture')
        if 'scripts/train.py' in cmd:
            (tmp_path / 'checkpoints/best_gb10.pt').write_bytes(b'fixture')
        return 0
    monkeypatch.setattr(module, 'run', fake_run)
    monkeypatch.setattr(module, 'check_gpu', lambda cfg: events.append(('preflight', cfg)))
    monkeypatch.setattr(module, 'package_run', lambda tag, cfg: events.append(('package', cfg)))
    module.main()
    prep = next(i for i, e in enumerate(events) if 'scripts/prepare_data.py' in e)
    gate = events.index(('preflight', 'configs/gb10_full.yaml'))
    train = next(i for i, e in enumerate(events) if 'scripts/train.py' in e)
    assert prep < gate < train
    assert events[0] == ('data', {'download': False})
    for cmd in events:
        if 'scripts/run_baseline.py' in cmd:
            assert cmd[cmd.index('--processed') + 1] == 'data/processed_gb10'
        if '--config' in cmd:
            assert cmd[cmd.index('--config') + 1] == 'configs/gb10_full.yaml'
    assert ('package', 'configs/gb10_full.yaml') in events


def test_failed_preflight_prevents_training(tmp_path, monkeypatch):
    module = launcher(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, 'argv', ['launch_training.py', '--train-only'])
    commands = []
    monkeypatch.setattr(module, 'run', lambda cmd, **kw: commands.append(cmd))
    def fail(config):
        raise SystemExit('preflight rejected fixture')
    monkeypatch.setattr(module, 'check_gpu', fail)
    with pytest.raises(SystemExit, match='preflight rejected'):
        module.main()
    assert not commands


def test_run_manifest_records_selected_configuration(tmp_path, monkeypatch):
    module = launcher(tmp_path, monkeypatch)
    module.package_run('fixture', 'configs/gb10_full.yaml')
    import json
    manifest = json.loads((tmp_path / 'results/run_fixture/run_manifest.json').read_text())
    assert manifest['config'] == 'configs/gb10_full.yaml'
