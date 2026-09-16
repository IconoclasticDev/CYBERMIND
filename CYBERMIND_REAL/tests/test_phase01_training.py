"""Phase 0/1 loss and validation safeguards, using synthetic graphs only."""
import importlib.util
from pathlib import Path
import sys
import torch
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
spec = importlib.util.spec_from_file_location('phase01_train', ROOT / 'scripts/train.py')
train = importlib.util.module_from_spec(spec); spec.loader.exec_module(train)
from cybermind.data.types import GraphState, GraphSequenceSample
from cybermind.losses import infiltration_loss, gaussian_transition_loss, graph_consistency_loss
from cybermind.models.world_model import WorldModel


def samples():
    return [GraphSequenceSample([
        GraphState(torch.randn(3, 14), torch.tensor([[0, 1], [1, 2]]), torch.zeros(2, 7),
                   ['a', 'b', 'c'], float(t), float(i == 0 and t > 0),
                   2 if i == 0 and t > 0 else 0, f's{i}', 'synthetic')
        for t in range(4)], f's{i}', 0., 60.) for i in range(3)]


def test_class_ratio_and_weighted_positive_loss():
    ratio, counts = train.training_class_weight(samples())
    assert ratio == 2. and counts == {'positive': 3, 'negative': 6}
    z = torch.zeros(1, requires_grad=True)
    assert torch.allclose(infiltration_loss(z, torch.ones(1), 2.), 2 * infiltration_loss(z, torch.ones(1)))
    with pytest.raises(ValueError): train.training_class_weight(samples()[1:])


def test_gaussian_variance_and_consistency_gradients():
    mean = torch.randn(2, 3, requires_grad=True); logvar = torch.zeros_like(mean, requires_grad=True)
    loss = gaussian_transition_loss(mean, torch.zeros_like(mean), logvar)
    loss.backward()
    assert torch.isfinite(mean.grad).all() and logvar.grad.abs().sum() > 0
    assert graph_consistency_loss(torch.zeros(2, 3, 4)) == 0
    assert graph_consistency_loss(torch.arange(12.).reshape(1, 3, 4)) > 0


def test_validation_metrics_and_split_leakage():
    metrics = train.validation_metrics(torch.tensor([.9, .8, .1, .2]), torch.tensor([1., 0., 1., 0.]))
    assert metrics['f1'] == .5 and metrics['precision'] == .5 and metrics['recall'] == .5
    with pytest.raises(ValueError, match='share graph windows'):
        train.assert_split_disjoint(samples(), samples())


def test_joint_backward_all_heads_and_regularizer():
    torch.set_num_threads(1)
    model = WorldModel(14, graph_hidden=8, graph_out=8, temporal_dim=16,
                       nhead=2, temporal_layers=1, graph_heads=2, num_stages=7, dropout=0.)
    cfg = {'model': {'num_stages': 7}, 'loss': {'transition': 1., 'infiltration': 1.,
            'stage': .5, 'calibration': .2, 'graph_consistency': .1, 'pos_weight': 2.}}
    loss, parts = train.batch_loss(model, samples(), cfg, torch.device('cpu'))
    assert torch.isfinite(loss) and parts['graph_consistency'] > 0
    loss.backward()
    for module in (model.graph, model.temporal, model.dynamics, model.infiltration_head, model.stage_head):
        gradients = [p.grad for p in module.parameters() if p.grad is not None]
        assert gradients and all(torch.isfinite(g).all() for g in gradients)
        assert sum(g.abs().sum() for g in gradients) > 0
    model.eval()
    a = train.batch_loss(model, samples(), cfg, torch.device('cpu'))[0]
    assert torch.isfinite(a)


def test_gb10_configuration():
    cfg = train.load_config(ROOT / 'configs/gb10_full.yaml')
    assert cfg['model']['graph_hidden'] == cfg['model']['temporal_dim'] == 512
    assert cfg['model']['num_stages'] == 7
    assert cfg['train']['precision'] == 'bf16'
    assert cfg['train']['selection_metric'] == 'val_f1_stage_band'
    assert cfg['train']['selection_f1_tolerance'] == .05
    assert cfg['train']['selection_stage_metric'] == 'stage'
    assert cfg['train']['require_cuda'] and cfg['data']['require_normalization']


def test_full_gb10_architecture_bf16_cpu_backward():
    torch.set_num_threads(1)
    cfg = train.load_config(ROOT / 'configs/gb10_full.yaml')
    cfg['loss']['pos_weight'] = 2.
    from cybermind.data.graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
    model = WorldModel(len(NODE_FEATURE_NAMES), **cfg['model'], **train.stage_model_kwargs(cfg))
    batch = samples()[:1]
    for state in batch[0].states:
        state.x = torch.randn(3, len(NODE_FEATURE_NAMES))
        state.edge_attr = torch.randn(state.edge_index.size(1), len(EDGE_FEATURE_NAMES))
    # This laptop's oneDNN backend lacks bf16 backward. Exercise portable
    # PyTorch kernels here; this is not a GB10 CUDA kernel certification.
    with torch.backends.mkldnn.flags(enabled=False):
        with train.autocast_context(torch.device('cpu'), 'bf16'):
            loss, parts = train.batch_loss(model, batch, cfg, torch.device('cpu'))
        loss.backward()
    assert torch.isfinite(loss)
    assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)


def test_durable_epoch_artifacts_and_rollout_monitor(tmp_path):
    payload = {'epoch': 1, 'value': torch.tensor([2.0])}
    checkpoint = tmp_path / 'epochs' / 'epoch_0001.pt'
    history = tmp_path / 'history.json'
    metrics = tmp_path / 'metrics.jsonl'
    train.atomic_torch_save(payload, checkpoint)
    train.atomic_json_write(history, [{'epoch': 1}])
    train.append_durable_jsonl(metrics, {'epoch': 1, 'loss': 0.5})
    assert torch.load(checkpoint, weights_only=False)['epoch'] == 1
    assert train.json.loads(history.read_text()) == [{'epoch': 1}]
    assert train.json.loads(metrics.read_text()) == {'epoch': 1, 'loss': 0.5}
    assert not list(tmp_path.rglob('*.tmp'))

    model = WorldModel(14, graph_hidden=8, graph_out=8, temporal_dim=16,
                       nhead=2, temporal_layers=1, graph_heads=2, num_stages=7,
                       dropout=0., use_crf_stage=True)
    cfg = {'eval': {'n_rollouts': 2}, 'train': {'collapse_monitor': {
        'rollout_steps': 4, 'n_rollouts': 2, 'seed': 0}}}
    result = train.rollout_stage_monitor(model, samples(), cfg, torch.device('cpu'))
    assert result['split'] == 'val' and len(result['per_step']) == 4
    assert all(step['samples'] == 3 and step['illegal_count'] == 0 for step in result['per_step'])
