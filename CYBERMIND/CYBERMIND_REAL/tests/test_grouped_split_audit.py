import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
spec = importlib.util.spec_from_file_location('split_audit', ROOT / 'scripts/audit_grouped_split.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample(timestamp, infiltration, stage):
    state = SimpleNamespace(timestamp=timestamp, y_infiltration=infiltration, y_stage=stage)
    return SimpleNamespace(states=[state])


def test_summary_counts_terminal_classes_and_stages():
    result = module.summarize([sample(1, 0, 0), sample(2, 1, 4)])
    assert result['terminal_targets'] == {'benign': 1, 'attack': 1}
    assert result['terminal_stages'] == {'0': 1, '4': 1}
    assert result['start_timestamp'] == 1 and result['end_timestamp'] == 2
