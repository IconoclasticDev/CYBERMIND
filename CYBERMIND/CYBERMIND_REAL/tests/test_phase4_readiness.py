"""Preparation must enforce packet coverage before expensive graph construction."""
import copy
import importlib.util
from pathlib import Path
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('fault', ['missing', 'nan', 'infinity', 'unavailable'])
def test_packet_contract_survives_canonical_compatibility_filling(fault):
    prep = script('prepare_data')
    frame = pd.DataFrame({'timestamp': ['2018-02-14'], 'src': ['a'], 'dst': ['b'],
                          'label': ['BENIGN'], 'source': ['CIC-IDS2018'],
                          **{name: [1.] for name in prep.PACKET_FEATURES}})
    if fault == 'missing':
        frame = frame.drop(columns=['ttl_mean'])
    elif fault == 'nan':
        frame['ttl_mean'] = float('nan')
    elif fault == 'infinity':
        frame['ttl_mean'] = float('inf')
    else:
        frame['packet_features_available'] = 0
    frame = prep.canonicalize(frame, 'fixture')
    with pytest.raises(ValueError, match='require_packet_features'):
        prep.prepare_frames([frame], {'data': {'require_packet_features': True}})
    prep.validate_packet_coverage([frame], {'data': {'require_packet_features': False}})


def test_complete_packet_contract_and_missing_columns():
    prep = script('prepare_data')
    frame = pd.DataFrame({name: [1.] for name in prep.PACKET_FEATURES})
    cfg = {'data': {'require_packet_features': True}}
    prep.validate_packet_coverage([frame], cfg)
    with pytest.raises(ValueError, match='missing'):
        prep.validate_packet_coverage([frame.drop(columns=['ttl_mean'])], cfg)


def test_four_configs_differ_only_in_ablation_flags_and_select_reviewed_policy():
    from cybermind.utils.checkpoint_selection import CheckpointSelection
    reference = None
    for name, edge, crf in [('full', True, True), ('edge_only', True, False),
                            ('crf_only', False, True), ('baseline', False, False)]:
        cfg = yaml.safe_load((ROOT / f'configs/gb10_{name}.yaml').read_text())
        assert cfg['model'].pop('use_edge_features') is edge
        assert cfg['loss'].pop('use_crf_stage') is crf
        assert cfg['data']['require_packet_features'] is True
        assert 'periodic_clock' not in cfg['model']
        assert cfg['train']['selection_metric'] == 'val_f1_stage_band'
        assert cfg['train']['selection_f1_tolerance'] == .05
        assert cfg['train']['selection_stage_metric'] == 'stage'
        CheckpointSelection(cfg['train'])
        if reference is not None:
            assert cfg == reference
        reference = cfg


def test_run_names_isolate_outputs_without_changing_training_policy():
    train = script('train')
    cfg = {'train': {'checkpoint': 'best_gb10.pt', 'history_path': 'results/history.json',
                     'selection_f1_tolerance': .05}}
    original = copy.deepcopy(cfg)
    train.apply_run_name(cfg, None)
    assert cfg == original
    train.apply_run_name(cfg, 'edge_only')
    assert Path(cfg['train']['checkpoint']).name == 'best_gb10_edge_only.pt'
    assert Path(cfg['train']['history_path']).name == 'history_edge_only.json'
    assert cfg['train']['selection_f1_tolerance'] == .05
    with pytest.raises(ValueError, match='run-name'):
        train.apply_run_name(cfg, '../escape')
