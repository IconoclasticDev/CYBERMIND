from pathlib import Path
import sys
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from cybermind.models.periodic_input import PeriodicClockInput
from cybermind.models.world_model import WorldModel
from cybermind.utils.config import edge_model_kwargs

SPEC = dict(column=2, slope=.25, intercept=-2., period=4.)


@pytest.mark.parametrize('device', ['cpu', 'cuda'])
def test_periodic_input_preserves_raw_and_extrapolates(device):
    if device == 'cuda' and not torch.cuda.is_available():
        pytest.skip('Actual CUDA required')
    transform = PeriodicClockInput(4, SPEC).to(device)
    x = torch.zeros(8, 4, device=device)
    x[:, 2] = torch.arange(8, device=device)*.25-2
    before = x.clone(); y = transform(x)
    assert torch.equal(x, before) and torch.equal(y[:, :4], x)
    assert torch.allclose(y[:4, 4:], y[4:, 4:], atol=1e-6)
    assert torch.unique(y[:4, 4:].round(decimals=5), dim=0).size(0) == 4
    x.requires_grad_(); transform(x).square().sum().backward()
    assert torch.isfinite(x.grad).all()


def test_periodic_checkpoint_and_default_off():
    options = dict(graph_hidden=8, graph_out=8, temporal_dim=8, nhead=2, temporal_layers=1, graph_heads=2, dropout=0.)
    torch.manual_seed(42); old = WorldModel(4, **options)
    torch.manual_seed(42); off = WorldModel(4, **options, periodic_clock=None)
    assert old.state_dict().keys() == off.state_dict().keys()
    assert all(torch.equal(v, off.state_dict()[k]) for k, v in old.state_dict().items())
    config = {'periodic_clock': SPEC}
    resolved = edge_model_kwargs({}, config)
    original = WorldModel(4, **options, **resolved)
    restored = WorldModel(4, **options, **resolved)
    restored.load_state_dict(original.state_dict(), strict=True)
    x = torch.randn(3, 4)
    assert torch.equal(original.periodic_input(x), restored.periodic_input(x))
    with pytest.raises(ValueError, match='checkpoint'):
        edge_model_kwargs({'periodic_clock': None}, config)


@pytest.mark.parametrize('changes', [{'slope': 0}, {'period': -1}, {'intercept': float('nan')}, {'column': 4}])
def test_invalid_periodic_definition(changes):
    with pytest.raises(ValueError):
        PeriodicClockInput(4, {**SPEC, **changes})
