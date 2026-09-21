"""Isolation is a topology sensitivity probe, not invented traffic measurements."""
from copy import deepcopy
import pytest
import torch
from cybermind.counterfactual.simulator import Intervention, mutate_state
from cybermind.data.types import GraphState
from cybermind.models.periodic_input import PeriodicClockInput


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
