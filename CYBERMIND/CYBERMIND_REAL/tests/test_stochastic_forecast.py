"""CPU shape/gradient smoke checks only; these do not establish model quality."""
import json
import sys
from pathlib import Path
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cybermind.data.types import GraphState
from cybermind.models.dynamics import DynamicsModel
from cybermind.models.temporal_encoder import TemporalTransformerEncoder
from cybermind.models.world_model import WorldModel


@pytest.fixture
def tiny():
    torch.manual_seed(17)
    torch.set_num_threads(1)
    model = WorldModel(3, graph_hidden=8, graph_out=8, temporal_dim=8,
                       nhead=2, temporal_layers=1, graph_heads=2, dropout=0.0)
    states = [GraphState(torch.randn(2, 3), torch.tensor([[0, 1], [1, 0]]),
                         torch.zeros(2, 7), ['a', 'b'], float(i), 0., 0, 'smoke', 'BENIGN')
              for i in range(3)]
    return model, states


def test_dynamics_shapes_and_reparameterized_gradient():
    model = DynamicsModel(8, 16)
    z = torch.randn(2, 3, 8, requires_grad=True)
    params = model(z)
    assert params['mean'].shape == params['logvar'].shape == z.shape
    sample = model.sample(**params)
    sample.square().mean().backward()
    assert model.logvar_net[-1].weight.grad.abs().sum() > 0
    assert z.grad is not None and torch.isfinite(z.grad).all()
    assert model.rollout(z[:, 0], 4).shape == (5, 2, 8)


def test_temporal_causality_and_attention():
    torch.manual_seed(1)
    encoder = TemporalTransformerEncoder(8, 8, 2, 2, 0.0).eval()
    x = torch.randn(1, 4, 8)
    first, attention = encoder(x, return_attention=True)
    changed = x.clone()
    changed[:, 2:] += 100
    second = encoder(changed)
    torch.testing.assert_close(first[:, :2], second[:, :2])
    assert attention.shape == (2, 1, 2, 4, 4)
    assert torch.count_nonzero(attention.triu(1)) == 0
    torch.testing.assert_close(attention.sum(-1), torch.ones_like(attention.sum(-1)))


@pytest.mark.parametrize('context', [torch.no_grad, torch.inference_mode])
def test_automatic_explanation_under_inference_context(tiny, context):
    model, states = tiny
    model.train()
    parameter = next(model.parameters())
    parameter.grad = torch.ones_like(parameter)
    with context():
        out = model.forecast(states, k=2, n_rollouts=4, seed=31)
    assert model.training
    assert torch.equal(parameter.grad, torch.ones_like(parameter))
    assert out['latent_samples'].shape == (4, 3, 8)
    assert out['stage_logits'].shape == (3, 7)
    assert out['infiltration_variance'].shape == (3,)
    assert out['infiltration_variance'][-1] > 0
    torch.testing.assert_close(out['infiltration_probability'], out['rollout_probabilities'].mean(0))
    explanation = out['explanation']
    json.dumps(explanation, allow_nan=False)
    assert len(explanation['gradient_x_input']) == 3
    assert len(explanation['temporal_attention']) == 3
    assert len(explanation['feature_occlusion']) == 3
    assert sum(x['attention'] for x in explanation['temporal_attention']) == pytest.approx(1.)
    for item in explanation['feature_occlusion']:
        assert item['risk_reduction'] == pytest.approx(item['baseline_risk'] - item['counterfactual_risk'])


def test_reproducible_rollouts_and_training_contract(tiny):
    model, states = tiny
    output = model.forward_batch([states, states])
    assert output['next_latents'].shape == output['next_logvar'].shape == (2, 2, 8)
    with torch.no_grad():
        a = model.forecast(states, 2, n_rollouts=8, seed=5, explain=False)
        b = model.forecast(states, 2, n_rollouts=8, seed=5, explain=False)
        c = model.forecast(states, 2, n_rollouts=8, seed=6, explain=False)
    assert 'explanation' not in a
    torch.testing.assert_close(a['rollout_probabilities'], b['rollout_probabilities'], rtol=0, atol=0)
    assert not torch.equal(a['rollout_probabilities'][:, 1:], c['rollout_probabilities'][:, 1:])
    # Observed step is shared; only future steps carry transition uncertainty.
    assert a['infiltration_variance'][0] == 0
