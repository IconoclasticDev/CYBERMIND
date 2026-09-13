import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('reviewed_frozen_gate', Path(__file__).resolve().parents[1]/'examples/phase3_second_escalation/frozen_gate.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def evidence():
    steps = [dict(step=i, samples=3, illegal_count=0, distinct_non_unknown=1, unknown_count=0) for i in range(1, 5)]
    history = [dict(train={'loss': -1., 'stage': .5, 'crf_stage': 1.}, val={'loss': -1., 'stage': .5, 'crf_stage': 1.})]
    return steps, history, [1., 2.]


def test_reviewed_frozen_gate_accepts_collapsed_but_active_legal_model():
    assert module.judge_frozen(*evidence())


@pytest.mark.parametrize('failure', ['illegal', 'missing_step', 'nan', 'zero_loss', 'zero_gradient'])
def test_reviewed_frozen_gate_rejects_mechanical_failures(failure):
    steps, history, gradients = evidence()
    if failure == 'illegal': steps[3]['illegal_count'] = 1
    if failure == 'missing_step': steps.pop()
    if failure == 'nan': history[0]['val']['loss'] = float('nan')
    if failure == 'zero_loss': history[0]['train']['stage'] = 0.
    if failure == 'zero_gradient': gradients[0] = 0.
    assert not module.judge_frozen(steps, history, gradients)
