"""Phase 3: real training and forecast for every edge/CRF flag combination."""
from dataclasses import replace
import importlib.util
import io
import math
import os
from pathlib import Path
import sys

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cybermind.data.types import GraphSequenceSample, GraphState
from cybermind.evaluation.metrics import illegal_transition_rate
from cybermind.models import graph_encoder
from cybermind.models.world_model import WorldModel

spec = importlib.util.spec_from_file_location("joint_features_train", ROOT / "scripts/train.py")
train = importlib.util.module_from_spec(spec)
spec.loader.exec_module(train)


def feature_combinations():
    edge = os.environ.get("CYBERMIND_TEST_EDGE_FEATURES")
    crf = os.environ.get("CYBERMIND_TEST_CRF_STAGE")
    if edge is None and crf is None:
        return [(False, False), (True, False), (False, True), (True, True)]
    if edge not in ("0", "1") or crf not in ("0", "1"):
        raise ValueError("Both CYBERMIND_TEST_EDGE_FEATURES and CYBERMIND_TEST_CRF_STAGE must be 0 or 1")
    return [(edge == "1", crf == "1")]


COMBINATIONS = feature_combinations()


def joint_sequences():
    generator = torch.Generator().manual_seed(316)
    # Competing incoming edges make edge attention observable in both layers.
    edges = torch.tensor([[0, 2, 1, 2, 0, 1], [1, 1, 0, 0, 2, 2]])
    return [GraphSequenceSample([
        GraphState(x=torch.randn(3, 4, generator=generator), edge_index=edges.clone(),
                   edge_attr=torch.randn(6, 7, generator=generator),
                   node_ids=["a", "b", "c"], timestamp=float(t),
                   y_infiltration=float(i == 1 and t > 0), y_stage=t if i else 0,
                   scenario_id=f"joint-{i}", attack_label="synthetic")
        for t in range(4)], f"joint-{i}", 0., 1.) for i in range(2)]


@pytest.mark.parametrize("device", ["cpu", "cuda"])
@pytest.mark.parametrize("use_edges,use_crf", COMBINATIONS,
                         ids=[f"edges-{int(edge)}-crf-{int(crf)}" for edge, crf in COMBINATIONS])
def test_joint_feature_execution_matrix(device, use_edges, use_crf, record_property):
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("Actual CUDA required for the Phase 3 exit matrix")
    if not graph_encoder.HAS_PYG:
        pytest.skip("Actual PyG required for the Phase 3 exit matrix")
    torch.set_num_threads(1)
    torch.manual_seed(319)
    options = dict(node_dim=4, graph_hidden=8, graph_out=8, temporal_dim=8,
                   nhead=2, temporal_layers=1, graph_heads=2, dropout=0.,
                   edge_attr_dim=7, use_edge_features=use_edges, use_crf_stage=use_crf)
    model = WorldModel(**options).to(device)
    batch = joint_sequences()
    cfg = {"model": {"num_stages": 7}, "loss": {
        "transition": 1., "infiltration": 1., "stage": .5, "crf_stage": .5,
        "calibration": .2, "graph_consistency": .1, "use_crf_stage": use_crf}}
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    loss, parts = train.batch_loss(model, batch, cfg, torch.device(device))
    assert torch.isfinite(loss) and all(math.isfinite(value) for value in parts.values())
    assert ("crf_stage" in parts) == use_crf
    loss.backward()
    gradients = [parameter.grad for parameter in model.parameters() if parameter.grad is not None]
    assert gradients and all(torch.isfinite(gradient).all() for gradient in gradients)
    assert model.stage_head.net[-1].weight.grad.norm() > 0
    for index, conv in enumerate((model.graph.conv1, model.graph.conv2), 1):
        if use_edges:
            gradient = conv.lin_edge.weight.grad
            assert gradient is not None and gradient.norm() > 0
            record_property(f"conv{index}_edge_gradient_norm", float(gradient.norm()))
        else:
            assert conv.lin_edge is None
    if use_crf:
        gradient = model.stage_decoder.transitions.grad
        assert gradient is not None and gradient.norm() > 0
        assert torch.count_nonzero(gradient[~model.stage_decoder.allowed_transitions]) == 0
        record_property("crf_transition_gradient_norm", float(gradient.norm()))
        record_property("crf_loss", parts["crf_stage"])
    else:
        assert not hasattr(model, "stage_decoder")
    optimizer.step()
    assert all(torch.isfinite(parameter).all() for parameter in model.parameters())

    states = [replace(state, x=state.x.to(device), edge_index=state.edge_index.to(device),
                      edge_attr=state.edge_attr.to(device)) for state in batch[1].states]
    with torch.no_grad():
        forecast = model.forecast(states, k=4, n_rollouts=3, seed=17, explain=False)
    assert forecast["decoded_stages"].shape == (5,)
    assert all(torch.isfinite(value).all() for value in forecast.values()
               if isinstance(value, torch.Tensor))
    rate = illegal_transition_rate(forecast["decoded_stages"])
    if use_crf:
        assert forecast["stage_decoding"] == "crf_viterbi" and rate == 0
    else:
        assert forecast["stage_decoding"] == "argmax"
        assert torch.equal(forecast["decoded_stages"], forecast["stage_logits"].argmax(-1))

    # A real optimizer update must survive strict serialization in all four modes.
    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    buffer.seek(0)
    restored = WorldModel(**options).to(device)
    restored.load_state_dict(torch.load(buffer, map_location=device, weights_only=True), strict=True)
    with torch.no_grad():
        reloaded = restored.forecast(states, k=4, n_rollouts=3, seed=17, explain=False)
    torch.testing.assert_close(forecast["infiltration_probability"], reloaded["infiltration_probability"],
                               atol=1e-6, rtol=1e-6)
    assert torch.equal(forecast["decoded_stages"], reloaded["decoded_stages"])

    record_property("device", device)
    record_property("backend", "pyg")
    record_property("use_edge_features", use_edges)
    record_property("use_crf_stage", use_crf)
    record_property("joint_loss", float(loss.detach()))
    record_property("all_gradients_finite", True)
    record_property("forecast_illegal_transition_rate", rate)
    record_property("strict_checkpoint_reload", True)
