"""Phase 1 edge conditioning: CPU/CUDA x PyG/fallback x off/on.

The matrix uses competing incoming edges (one incoming edge makes an
attention softmax constant). CUDA skips are convenient for CPU installs;
Phase 1 exit evidence must show all eight matrix cases actually passing.
"""
from dataclasses import replace
from pathlib import Path
import sys

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cybermind.data.types import GraphState
from cybermind.models import graph_encoder
from cybermind.models.graph_encoder import DenseGraphAttention
from cybermind.models.world_model import WorldModel


def graph_sequences(device="cpu"):
    generator = torch.Generator().manual_seed(710)
    edges = torch.tensor([[0, 2, 1, 2, 0, 1], [1, 1, 0, 0, 2, 2]], device=device)
    return [[GraphState(
        x=torch.randn(3, 14, generator=generator).to(device),
        edge_index=edges.clone(),
        edge_attr=torch.randn(6, 27, generator=generator).to(device),
        node_ids=["a", "b", "c"], timestamp=float(window),
        y_infiltration=float(sequence), y_stage=sequence,
        scenario_id=f"edge-test-{sequence}", attack_label="synthetic",
    ) for window in range(2)] for sequence in range(2)]


def build_model(monkeypatch, backend, enabled, device="cpu", edge_attr_dim=27):
    if backend == "pyg" and graph_encoder.GATv2Conv is None:
        pytest.skip("PyG unavailable; not sufficient for the Phase 1 exit matrix")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA unavailable; not sufficient for the Phase 1 exit matrix")
    monkeypatch.setattr(graph_encoder, "HAS_PYG", backend == "pyg")
    torch.manual_seed(611)
    model = WorldModel(
        14, graph_hidden=8, graph_out=8, temporal_dim=16,
        nhead=2, temporal_layers=1, graph_heads=2, dropout=0.,
        edge_attr_dim=edge_attr_dim, use_edge_features=enabled,
    ).to(device)
    assert model.graph.has_pyg == (backend == "pyg")
    return model


def assert_finite_backward(model, tensors, enabled, record_property=None, prefix=""):
    model.zero_grad(set_to_none=True)
    loss = sum((value * torch.linspace(.1, 1.3, value.numel(),
               device=value.device).reshape_as(value)).sum() for value in tensors)
    assert torch.isfinite(loss)
    loss.backward()
    gradients = [p.grad for p in model.parameters() if p.grad is not None]
    assert gradients and all(torch.isfinite(g).all() for g in gradients)
    assert sum(g.abs().sum().item() for g in gradients) > 0
    if record_property is not None:
        record_property(f"{prefix}_loss", loss.detach().item())
        record_property(f"{prefix}_all_gradients_finite", True)
        graph_grad_norm = sum(p.grad.abs().sum().item() for p in model.graph.parameters()
                              if p.grad is not None)
        assert graph_grad_norm > 0
        record_property(f"{prefix}_graph_gradient_l1", graph_grad_norm)
    if enabled:
        for index, conv in enumerate((model.graph.conv1, model.graph.conv2), start=1):
            projection = conv.lin_edge if model.graph.has_pyg else conv.edge_proj
            assert projection.weight.grad is not None
            assert torch.isfinite(projection.weight.grad).all()
            assert projection.weight.grad.abs().sum().item() > 0
            if record_property is not None:
                record_property(f"{prefix}_conv{index}_edge_gradient_l1",
                                projection.weight.grad.abs().sum().item())


def test_fallback_attention_is_destination_conditioned_and_adds_self_loops():
    layer = DenseGraphAttention(2, 2, heads=1, dropout=0.).eval()
    with torch.no_grad():
        layer.lin.weight.copy_(torch.eye(2))
        layer.att.copy_(torch.tensor([[1., -1.]]))
    x = torch.tensor([[2., 0.], [0., 2.], [-3., 0.], [0., -3.]])
    edges = torch.tensor([[0, 1, 0, 1], [2, 2, 3, 3]])
    _, (indices, weights) = layer(x, edges, return_attention_weights=True)
    first = weights[:2, 0]
    second = weights[2:4, 0]
    assert not torch.allclose(first, second)
    assert indices.shape[1] == edges.shape[1] + x.shape[0]
    assert torch.equal(indices[:, -x.shape[0]:], torch.arange(4).repeat(2, 1))


@pytest.mark.parametrize("device", ["cpu", "cuda"])
@pytest.mark.parametrize("backend", ["pyg", "fallback"])
@pytest.mark.parametrize("enabled", [False, True], ids=["edges-off", "edges-on"])
def test_edge_attention_execution_matrix(monkeypatch, device, backend, enabled, record_property):
    torch.set_num_threads(1)
    model = build_model(monkeypatch, backend, enabled, device)
    record_property("device", device)
    record_property("backend", backend)
    record_property("use_edge_features", enabled)
    record_property("edge_attr_dim", 27)
    batch = graph_sequences(device)
    embedded = model.encode_state(batch[0][0])
    assert embedded.shape == (16,)
    assert_finite_backward(model, [embedded], enabled, record_property, "encode_state")
    single = model(batch[0])
    assert single["graph_embeddings"].shape == (2, 16)
    assert single["next_latents"].shape == (1, 16)
    assert_finite_backward(model, [v for v in single.values() if isinstance(v, torch.Tensor)],
                           enabled, record_property, "forward")
    batched = model.forward_batch(batch)
    assert batched["graph_embeddings"].shape == (2, 2, 16)
    assert batched["next_latents"].shape == (2, 1, 16)
    assert_finite_backward(model, list(batched.values()), enabled, record_property, "forward_batch")

    model.eval()
    state = batch[0][0]
    changed = replace(state, edge_attr=state.edge_attr.flip(0) * 4)
    with torch.no_grad():
        original = model.encode_state(state)
        perturbed = model.encode_state(changed)
    record_property("edge_perturbation_max_abs_change", (original - perturbed).abs().max().item())
    if enabled:
        assert (original - perturbed).abs().max().item() > 1e-6
    elif device == "cuda" and backend == "pyg":
        # Atomic scatter reductions may reorder additions even with identical
        # inputs. This is numerical noise, not use of the disabled attributes.
        torch.testing.assert_close(original, perturbed, atol=1e-6, rtol=1e-6)
    else:
        assert torch.equal(original, perturbed)


@pytest.mark.parametrize("backend", ["pyg", "fallback"])
def test_disabled_checkpoint_and_initialization_compatibility(monkeypatch, backend):
    legacy_default = build_model(monkeypatch, backend, False, edge_attr_dim=None)
    configured_off = build_model(monkeypatch, backend, False, edge_attr_dim=27)
    legacy_state = legacy_default.state_dict()
    assert legacy_state.keys() == configured_off.state_dict().keys()
    assert all(torch.equal(value, configured_off.state_dict()[key])
               for key, value in legacy_state.items())
    configured_off.load_state_dict(legacy_state, strict=True)
    state = graph_sequences()[0][0]
    legacy_default.eval()
    configured_off.eval()
    with torch.no_grad():
        assert torch.equal(legacy_default.encode_state(state), configured_off.encode_state(state))


@pytest.mark.parametrize("backend", ["pyg", "fallback"])
@pytest.mark.parametrize("bad_attr", [torch.zeros(5, 27), torch.zeros(6, 28),
                                       torch.zeros(6), torch.zeros(6, 27, dtype=torch.long)])
def test_enabled_rejects_malformed_attributes_disabled_ignores(monkeypatch, backend, bad_attr):
    state = graph_sequences()[0][0]
    malformed = replace(state, edge_attr=bad_attr)
    enabled = build_model(monkeypatch, backend, True)
    with pytest.raises((ValueError, TypeError)):
        enabled.encode_state(malformed)
    disabled = build_model(monkeypatch, backend, False).eval()
    with torch.no_grad():
        assert torch.equal(disabled.encode_state(state), disabled.encode_state(malformed))


@pytest.mark.parametrize("backend", ["pyg", "fallback"])
def test_empty_edges_and_attributes_are_supported(monkeypatch, backend):
    model = build_model(monkeypatch, backend, True)
    state = graph_sequences()[0][0]
    state = replace(state, edge_index=torch.empty(2, 0, dtype=torch.long),
                    edge_attr=torch.empty(0, 27))
    output = model.encode_state(state)
    assert output.shape == (16,) and torch.isfinite(output).all()


@pytest.mark.parametrize("backend", ["pyg", "fallback"])
def test_enabled_missing_attributes_uses_node_only_attention(monkeypatch, backend):
    model = build_model(monkeypatch, backend, True).eval()
    state = graph_sequences()[0][0]
    with torch.no_grad():
        absent = model.encode_state(replace(state, edge_attr=None))
        zeroed = model.encode_state(replace(state, edge_attr=torch.zeros_like(state.edge_attr)))
    assert torch.isfinite(absent).all()
    torch.testing.assert_close(absent, zeroed, atol=1e-6, rtol=1e-5)


@pytest.mark.parametrize("backend", ["pyg", "fallback"])
@pytest.mark.parametrize("edge_attr_dim", [None, 0, -1])
def test_enabled_requires_positive_edge_dimension(monkeypatch, backend, edge_attr_dim):
    with pytest.raises((ValueError, TypeError)):
        build_model(monkeypatch, backend, True, edge_attr_dim=edge_attr_dim)
