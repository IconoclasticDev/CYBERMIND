"""Train-only stage balancing is optional and leaves CRF likelihood unchanged."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stage_weight_train', ROOT / 'scripts/train.py')
train = importlib.util.module_from_spec(spec)
spec.loader.exec_module(train)


def samples(*sequences):
    return [SimpleNamespace(states=[SimpleNamespace(y_stage=y) for y in seq]) for seq in sequences]


def test_weights_count_training_targets_only_and_preserve_rng():
    dataset = samples([2, 0, 0, 0], [2, 1])
    rng = torch.random.get_rng_state().clone()
    cfg = {'model': {'num_stages': 3}, 'loss': {'stage_class_balance': True}}
    train.configure_stage_class_weights(cfg, dataset)
    assert cfg['loss']['stage_class_counts'] == [3, 1, 0]
    assert cfg['loss']['stage_class_weights'] == pytest.approx([2 / 3, 2., 1.])
    assert torch.equal(rng, torch.random.get_rng_state())
    # Validation can only consume these stored weights; it cannot fit them.
    saved = deepcopy(cfg)
    train.stage_cross_entropy(torch.zeros(2, 3), torch.tensor([2, 2]), cfg['loss'])
    assert cfg == saved


@pytest.mark.parametrize('flag', ['false', 0, 1, None])
def test_balance_flag_is_strict_boolean(flag):
    with pytest.raises(ValueError, match='boolean'):
        train.configure_stage_class_weights({'loss': {'stage_class_balance': flag}}, [])


@pytest.mark.parametrize('weights', [None, [1.], [1., 0.], [1., -1.],
                                    [1., float('nan')], [1., float('inf')], [True, 1.], ['1', 1.]])
def test_invalid_weights_fail_explicitly(weights):
    with pytest.raises(ValueError, match='finite positive'):
        train.stage_cross_entropy(torch.zeros(2, 2), torch.tensor([0, 1]),
                                  {'stage_class_balance': True, 'stage_class_weights': weights})


@pytest.mark.parametrize('dataset', [[], samples([0]), samples([0, -1]), samples([0, 3]), samples([0, 1.5])])
def test_invalid_training_supervision_fails(dataset):
    with pytest.raises(ValueError):
        train.training_stage_class_weights(dataset, 3)


def test_default_off_has_exact_loss_gradients_and_no_rng_effect():
    logits = torch.tensor([[2., -1.], [0., 1.], [-2., 2.]], requires_grad=True)
    labels = torch.tensor([0, 0, 1])
    expected = F.cross_entropy(logits, labels)
    expected_gradient = torch.autograd.grad(expected, logits)[0]
    rng = torch.random.get_rng_state().clone()
    for loss_config in [{}, {'stage_class_balance': False, 'stage_class_weights': 'ignored'}]:
        actual = train.stage_cross_entropy(logits, labels, loss_config)
        assert torch.equal(expected, actual)
        assert torch.equal(expected_gradient, torch.autograd.grad(actual, logits)[0])
    assert torch.equal(rng, torch.random.get_rng_state())
    cfg = {'loss': {}}
    train.configure_stage_class_weights(cfg, None)
    assert cfg == {'loss': {}}


def test_weighted_gradient_balances_class_mass():
    logits = torch.zeros(4, 2, requires_grad=True)
    labels = torch.tensor([0, 0, 0, 1])
    loss = train.stage_cross_entropy(logits, labels,
        {'stage_class_balance': True, 'stage_class_weights': [2 / 3, 2.]})
    loss.backward()
    assert torch.isfinite(loss) and torch.isfinite(logits.grad).all()
    assert logits.grad[:3].abs().sum() == pytest.approx(float(logits.grad[3:].abs().sum()))
    assert logits.grad[3].abs().sum() == pytest.approx(3 * float(logits.grad[0].abs().sum()))


@pytest.mark.parametrize('device', ['cpu', 'cuda'])
def test_batch_loss_changes_ce_only_with_fixed_draws(device):
    if device == 'cuda' and not torch.cuda.is_available():
        pytest.skip('Actual CUDA required for weighted StageHead integration')
    # Reuse realistic existing integration inputs, while asserting the distinct
    # balancing contract here rather than duplicating decoder correctness tests.
    integration_spec = importlib.util.spec_from_file_location('stage_weight_inputs', ROOT / 'tests/test_stage_integration.py')
    inputs = importlib.util.module_from_spec(integration_spec)
    integration_spec.loader.exec_module(inputs)
    torch.set_num_threads(1)
    model = inputs.tiny_model(True, device=device)
    batch = inputs.sequences()
    cfg = {'model': {'num_stages': 7}, 'loss': {'stage': .5, 'crf_stage': .5, 'use_crf_stage': True}}
    torch.manual_seed(812)
    unweighted, before = train.batch_loss(model, batch, cfg, torch.device(device))
    cfg['loss']['stage_class_balance'] = True
    train.configure_stage_class_weights(cfg, batch)
    torch.manual_seed(812)
    weighted, after = train.batch_loss(model, batch, cfg, torch.device(device))
    assert before['stage'] != after['stage']
    for key in before.keys() - {'stage'}:
        assert before[key] == after[key]
    assert float((weighted - unweighted).detach()) == pytest.approx(.5 * (after['stage'] - before['stage']), abs=1e-6)
    weighted.backward()
    assert torch.isfinite(model.stage_head.net[-1].weight.grad).all()
    assert model.stage_head.net[-1].weight.grad.norm() > 0
