import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from cybermind.utils.checkpoint_selection import CheckpointSelection

CFG = dict(selection_metric='val_f1_stage_band', selection_f1_tolerance=.05, selection_stage_metric='stage')


def test_clear_improvement_overrides_stage_but_outside_band_cannot():
    s = CheckpointSelection(CFG)
    assert s.update(1, {'f1': .8, 'stage': .2})
    assert s.update(2, {'f1': .9, 'stage': .8})
    assert not s.update(3, {'f1': .84, 'stage': .01})
    assert s.selected_epoch == 2
    assert s.update(4, {'f1': .88, 'stage': .7})
    assert s.best_f1 == .9 and s.selected_epoch == 4


def test_band_boundaries_and_equal_stage_retain_prior_selection():
    s = CheckpointSelection(CFG)
    s.update(1, {'f1': .5, 'stage': 1.})
    assert not s.update(2, {'f1': .55, 'stage': 2.})
    assert s.best_f1 == .5  # Exact reviewer anchor semantics, not unconditional maximum.
    assert s.update(3, {'f1': .45, 'stage': .9})
    assert not s.update(4, {'f1': .5, 'stage': .9})
    assert s.selected_epoch == 3


def test_default_policy_ignores_stage_and_retains_min_delta():
    s = CheckpointSelection({'min_delta': .01})
    assert s.update(1, {'f1': .8})
    assert not s.update(2, {'f1': .805, 'stage': 0.})
    assert not s.update(3, {'f1': .8, 'stage': -100.})
    assert s.update(4, {'f1': .82})
    assert s.selected_epoch == 4


@pytest.mark.parametrize('changes', [{'selection_f1_tolerance': None}, {'selection_f1_tolerance': float('nan')},
    {'selection_f1_tolerance': -.01}, {'selection_f1_tolerance': 1.1}, {'selection_f1_tolerance': True},
    {'selection_stage_metric': 'loss'}, {'min_delta': .01}, {'selection_metric': 'test_f1'}])
def test_invalid_policy_is_rejected(changes):
    with pytest.raises(ValueError): CheckpointSelection({**CFG, **changes})


@pytest.mark.parametrize('metrics', [{'f1': float('nan'), 'stage': 1.}, {'f1': .5, 'stage': float('inf')}, {'f1': .5, 'stage': -1.}])
def test_invalid_validation_metrics_rejected(metrics):
    with pytest.raises(ValueError): CheckpointSelection(CFG).update(1, metrics)
