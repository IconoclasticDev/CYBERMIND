"""Exercise the synthetic probe without certifying real-data readiness."""
import importlib.util
from pathlib import Path
import sys
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('gpu_preflight_test', ROOT/'scripts/gpu_preflight.py')
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


@pytest.mark.parametrize('edge,crf', [(False,False),(True,False),(False,True),(True,True)])
def test_probe_actual_loss_gradients_and_scope(edge, crf):
    cfg = yaml.safe_load((ROOT/'configs/gb10_full.yaml').read_text())
    cfg['model'].update(graph_hidden=8, graph_out=8, temporal_dim=8, graph_heads=2,
                        nhead=2, temporal_layers=1, dropout=0., use_edge_features=edge)
    cfg['loss']['use_crf_stage'] = crf
    cfg['data']['history'] = 4
    cfg['train']['precision'] = 'fp32'
    result = preflight.synthetic_model_probe(cfg, 'cpu')
    assert result['passed'] and result['mode'] == 'synthetic'
    assert result['history'] == 4 and result['batch_size'] == 1
    assert cfg['data']['require_packet_features'] is True
    assert ('crf' in result['active_gradient_groups']) is crf
    assert ('conv1_edge_projection' in result['active_gradient_groups']) is edge
    assert ('conv2_edge_projection' in result['active_gradient_groups']) is edge
    assert result['peak_reserved_bytes'] is None
    assert 'does not verify real corpus' in result['scope']


def test_probe_rejects_invalid_reviewed_selection():
    cfg = yaml.safe_load((ROOT/'configs/gb10_full.yaml').read_text())
    cfg['train']['min_delta'] = .0001
    with pytest.raises(ValueError):
        preflight.synthetic_model_probe(cfg, 'cpu')
