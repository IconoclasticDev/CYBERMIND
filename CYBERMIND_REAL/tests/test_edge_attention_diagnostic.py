"""Test raw-scale selection, real coefficients, self-loop exclusion and RNG safety."""
from types import SimpleNamespace
import pytest
import torch
from cybermind.evaluation.edge_attention import EdgeAttentionDiagnostic
from cybermind.models import graph_encoder


def normalization():
    return {'edge': {'features':['bytes','port'], 'mean':[1000.,80.], 'std':[100.,10.]}}


def state():
    return SimpleNamespace(x=torch.randn(3,4), edge_index=torch.tensor([[0,2,1],[1,1,1]]),
                           edge_attr=torch.tensor([[2.,0.],[-9.,0.],[20.,0.]]))


def test_raw_threshold_exact_pooling_excludes_selfloops():
    s = state()
    weights = torch.tensor([[.2,.4],[.5,.6],[.3,0.]])
    graph = SimpleNamespace(use_edge_features=True, has_pyg=True,
                            attention_weights=lambda *args: [(s.edge_index,weights),(s.edge_index,weights)])
    diagnostic = EdgeAttentionDiagnostic(SimpleNamespace(graph=graph), normalization(),1100)
    diagnostic.observe([s])
    r = diagnostic.report()
    assert r['selected_edge_occurrences'] == 1
    assert r['observed_nonself_edge_occurrences'] == 2
    assert r['coefficient_count'] == 4
    assert r['mean_attention'] == pytest.approx(.3)
    diagnostic = EdgeAttentionDiagnostic(SimpleNamespace(graph=graph), normalization(),10000)
    diagnostic.observe([s])
    assert diagnostic.report()['mean_attention'] is None
    assert diagnostic.report()['status'] == 'no_matching_edges'
    # Raw aggregate port outside the common list independently selects an edge.
    s.edge_attr[1,1] = 13.7
    diagnostic.observe([s])
    assert diagnostic.report()['selected_edge_occurrences'] == 1


@pytest.mark.parametrize('pyg', [False,True])
def test_real_layer_coefficients_do_not_change_forward_or_rng(monkeypatch,pyg):
    monkeypatch.setattr(graph_encoder,'HAS_PYG',pyg)
    graph=graph_encoder.GATv2GraphEncoder(4,8,8,heads=2,dropout=.1,edge_attr_dim=2,use_edge_features=True).eval()
    s=state()
    with torch.no_grad():
        before=graph(s.x,s.edge_index,s.edge_attr)
        rng=torch.get_rng_state().clone()
        diagnostic=EdgeAttentionDiagnostic(SimpleNamespace(graph=graph),normalization(),1100)
        diagnostic.observe([s])
        assert torch.equal(rng,torch.get_rng_state())
        assert torch.equal(before,graph(s.x,s.edge_index,s.edge_attr))
    r=diagnostic.report()
    assert r['status']=='ok' and 0 <= r['mean_attention'] <= 1
    assert r['coefficient_count']==4
    for indices,weights in graph.attention_weights(s.x,s.edge_index,s.edge_attr):
        for destination in indices[1].unique():
            assert torch.allclose(weights[indices[1]==destination].sum(0),torch.ones(2),atol=1e-6)
    graph.train()
    with pytest.raises(ValueError,match='evaluation mode'):
        graph.attention_weights(s.x,s.edge_index,s.edge_attr)


def test_disabled_and_missing_normalizer_are_explicit():
    graph=SimpleNamespace(use_edge_features=False,has_pyg=True)
    diagnostic=EdgeAttentionDiagnostic(SimpleNamespace(graph=graph),None)
    diagnostic.observe([state()])
    assert diagnostic.report()['status']=='disabled_edge_features'
    assert diagnostic.report()['mean_attention'] is None
    graph.use_edge_features=True
    assert EdgeAttentionDiagnostic(SimpleNamespace(graph=graph),None).report()['status']=='unavailable_normalization'
