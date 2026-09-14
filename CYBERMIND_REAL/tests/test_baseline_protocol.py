"""Protect the benchmark against target leakage and misleading FPR/parity."""
from copy import deepcopy
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from cybermind.baselines.protocol import features, sample_target, metric_report, evaluate_baseline
from cybermind.baselines.logistic import LogisticBaseline


def sample(label=0, value=1.0):
    def state(y, x):
        return SimpleNamespace(x=torch.tensor([[x, 2.0], [x, 4.0]]),
                               edge_attr=torch.tensor([[5.0, 6.0]]),
                               y_infiltration=y, timestamp=x)
    return SimpleNamespace(states=[state(1, value), state(label, value + 100)],
                           scenario_id=str(value))


def test_target_window_features_and_history_labels_cannot_leak():
    original = sample(0)
    modified = deepcopy(original)
    modified.states[-1].x.fill_(999)
    modified.states[-1].edge_attr.fill_(-999)
    modified.states[0].y_infiltration = 0
    np.testing.assert_array_equal(features(original), features(modified))
    assert sample_target(original) == 0  # history contains a positive label
    modified.states[-1].y_infiltration = 1
    assert sample_target(modified) == 1
    np.testing.assert_array_equal(features(original), features(modified))


def test_edge_coverage_is_explicit_and_changes_only_edge_mode():
    original = sample()
    changed = deepcopy(original)
    changed.states[0].edge_attr *= 2
    np.testing.assert_array_equal(features(original, 'node'), features(changed, 'node'))
    assert not np.array_equal(features(original), features(changed))
    assert features(original).shape == (4,)


def test_empty_edges_keep_fixed_width():
    value = sample()
    value.states[0].edge_attr = torch.empty(0, 2)
    np.testing.assert_array_equal(features(value), [1, 3, 0, 0])


def test_periodic_transform_exactly_matches_model_input():
    from cybermind.models.periodic_input import PeriodicClockInput
    value = sample()
    spec = {'column': 0, 'slope': 1.0, 'intercept': 0.0, 'period': 4.0}
    expected = PeriodicClockInput(2, spec)(value.states[0].x).mean(0).numpy()
    np.testing.assert_array_equal(features(value, 'node', spec), expected)


def test_fpr_uses_negative_denominator_and_fixed_threshold():
    metrics, counts = metric_report([0, 0, 0, 1], [.8, .2, .4, .9], .5)
    assert counts == {'tn': 2, 'fp': 1, 'fn': 0, 'tp': 1}
    assert metrics['fpr'] == pytest.approx(1 / 3)
    assert metric_report([0, 0, 0, 1], [.8, .2, .4, .9], .9)[0]['fpr'] == 0


@pytest.mark.parametrize('targets,expected', [([1, 1], None), ([0, 0], 0.0), ([], None)])
def test_undefined_fpr_not_advertised_as_zero(targets, expected):
    metrics, _ = metric_report(targets, [0.1] * len(targets), .5)
    assert metrics['fpr'] == expected


@pytest.mark.parametrize('label', [0, 1])
def test_single_class_dummy_still_reports_full_metrics(tmp_path, label):
    torch.save([sample(label)], tmp_path / 'train.pt')
    torch.save([sample(0, 2.0), sample(1, 3.0)], tmp_path / 'test.pt')
    result = evaluate_baseline(tmp_path)
    assert result['baseline'] == 'dummy_prior_single_class'
    assert result['metrics']['fpr'] == float(label)
    assert set(result['metrics']) == {'f1', 'precision', 'recall', 'fpr', 'ap', 'roc_auc'}
    assert result['protocol']['input'].startswith('states[:-1]')


def test_logistic_metrics_include_fpr():
    model = LogisticBaseline().fit(np.array([[0], [1], [2], [3]]), [0, 0, 1, 1])
    assert model.metrics(np.array([[0], [3]]), [0, 1])['fpr'] == 0


@pytest.mark.parametrize('threshold', [-.1, 1.1, float('nan')])
def test_invalid_threshold_rejected(threshold):
    with pytest.raises(ValueError, match='threshold'):
        metric_report([0, 1], [.1, .9], threshold)


@pytest.mark.parametrize('targets,probabilities', [
    ([0, 1], [.5]), ([2], [.5]), ([0], [float('nan')]), ([1], [1.1]),
])
def test_invalid_metric_inputs_rejected(targets, probabilities):
    with pytest.raises(ValueError):
        metric_report(targets, probabilities, .5)


def test_dummy_path_does_not_hide_feature_schema_mismatch(tmp_path):
    torch.save([sample(0)], tmp_path / 'train.pt')
    value = sample(0)
    value.states[0].x = torch.ones(2, 3)
    torch.save([value], tmp_path / 'test.pt')
    with pytest.raises(ValueError, match='widths differ'):
        evaluate_baseline(tmp_path)
