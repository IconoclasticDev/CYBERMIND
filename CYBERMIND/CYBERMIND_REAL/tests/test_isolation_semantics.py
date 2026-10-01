"""Isolation is a topology sensitivity probe, not invented traffic measurements."""
from copy import deepcopy
import pytest
import torch
from cybermind.counterfactual.simulator import Intervention, mutate_state
from cybermind.data.types import GraphState
from cybermind.models.periodic_input import PeriodicClockInput
from cybermind.data.graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
from cybermind.data.normalization import FeatureNormalizer


def graph():
    return GraphState(torch.tensor([[2.5, -1.0], [2.5, -1.0], [1.0, 3.0]]),
                      torch.tensor([[0, 1, 1, 2], [1, 0, 2, 1]]),
                      torch.arange(8, dtype=torch.float32).reshape(4, 2),
                      ['a', 'b', 'c'], 10, 0, 0, 'case', 'Benign',
                      {'normalization_fingerprint': 'unchanged', 'campaign_reset': False})


@pytest.mark.parametrize('action', ['Isolate Host', 'Block Host'])
def test_cut_preserves_measurements_and_alignment_without_mutating_input(action):
    original = graph()
    snapshot = deepcopy(original)
    altered = mutate_state(original, Intervention(action, host=0))
    assert torch.equal(altered.x, original.x)
    assert torch.equal(altered.edge_index, torch.tensor([[1, 2], [2, 1]]))
    assert torch.equal(altered.edge_attr, original.edge_attr[2:])
    assert altered.metadata == original.metadata
    assert altered.node_ids == original.node_ids
    for key in ('x', 'edge_index', 'edge_attr'):
        assert torch.equal(getattr(original, key), getattr(snapshot, key))
    altered.x.fill_(0)
    assert torch.equal(original.x, snapshot.x)


@pytest.mark.parametrize('host', [-1, 3, True, 0.5, '0'])
def test_invalid_host_rejected(host):
    with pytest.raises(ValueError, match='valid node index'):
        mutate_state(graph(), Intervention('Isolate Host', host=host))


def test_periodic_clock_representation_is_invariant_under_isolation():
    original = graph()
    transform = PeriodicClockInput(2, {'column': 0, 'slope': 1., 'intercept': 0., 'period': 4.})
    isolated = mutate_state(original, Intervention('Isolate Host', host=0))
    assert torch.equal(transform(original.x), transform(isolated.x))


def test_isolation_is_idempotent():
    once = mutate_state(graph(), Intervention('Isolate Host', host=0))
    twice = mutate_state(once, Intervention('Isolate Host', host=0))
    assert torch.equal(once.x, twice.x)
    assert torch.equal(once.edge_index, twice.edge_index)
    assert torch.equal(once.edge_attr, twice.edge_attr)


def normalizer():
    def block(names):
        return {'features': list(names), 'count': 2,
                'mean': [10.] * len(names), 'std': [2.] * len(names)}
    return FeatureNormalizer({'version': 1, 'fit_split': 'train', 'dtype': 'float32',
                              'method': 'population_mean_std', 'training_windows': 1,
                              'node': block(NODE_FEATURE_NAMES), 'edge': block(EDGE_FEATURE_NAMES)})


def normalized_graph():
    norm = normalizer()
    raw_x = torch.full((2, len(NODE_FEATURE_NAMES)), 10.)
    raw_edge = torch.full((2, len(EDGE_FEATURE_NAMES)), 10.)
    raw_edge[:, 3] = torch.tensor([80., 443.])
    return GraphState(norm.transform(raw_x, 'node'), torch.tensor([[0, 1], [1, 0]]),
                      norm.transform(raw_edge, 'edge'), ['a', 'b'], 10, 0, 0,
                      'normalized', 'Benign', {'normalization_fingerprint': norm.fingerprint}), norm


def test_raw_value_mutations_inverse_transform_then_renormalize():
    original, norm = normalized_graph()
    limited = mutate_state(original, Intervention('Rate Limit', factor=.5), norm)
    raw = norm.inverse_transform(limited.x, 'node')
    torch.testing.assert_close(raw[:, :4], torch.full((2, 4), 5.))
    torch.testing.assert_close(raw[:, 4:], torch.full_like(raw[:, 4:], 10.))
    blocked = mutate_state(original, Intervention('Block Port', port=443), norm)
    assert blocked.edge_index.shape[1] == 1
    assert int(norm.inverse_transform(blocked.edge_attr, 'edge')[0, 3]) == 80


def test_normalized_raw_value_mutation_requires_matching_constants():
    original, _ = normalized_graph()
    with pytest.raises(ValueError, match='requires checkpoint normalization'):
        mutate_state(original, Intervention('Rate Limit', factor=.5))
