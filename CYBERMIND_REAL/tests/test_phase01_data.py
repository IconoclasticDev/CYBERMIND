"""Synthetic Phase 0/1 correctness checks; no real-corpus metric claims."""
import importlib.util
from pathlib import Path
import sys
import pandas as pd
import pytest
import torch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
spec = importlib.util.spec_from_file_location('prepare_phase01', ROOT / 'scripts/prepare_data.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
from cybermind.data.normalization import FeatureNormalizer
from cybermind.data.graph_builder import build_graph_state, NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
from cybermind.data.adapters.unified import UnifiedAdapter

CFG = {'data': {'window_seconds': 1, 'stride_seconds': 1, 'history': 2}}


def events(n=100, offset=0, volume=10, source='CIC-IDS2018'):
    return pd.DataFrame({'timestamp': pd.date_range('2018-02-14', periods=n + offset, freq='s')[offset:],
                         'src': '10.0.0.1', 'dst': '10.0.0.2', 'label': 'BENIGN',
                         'source': source, 'bytes_fwd': volume, 'packets_fwd': 1})


def test_chain_crosses_files_and_keeps_host_identity():
    later = prepare.canonicalize(events(50, 50), 'a_later.csv')
    earlier = prepare.canonicalize(events(50), 'z_earlier.csv')
    splits, normalizer, reports = prepare.prepare_frames([later, earlier], CFG)
    assert len({s.scenario_id for bucket in splits.values() for s in bucket}) == 1
    assert any(s.states[0].timestamp < pd.Timestamp('2018-02-14 00:00:50').timestamp() <= s.states[-1].timestamp for s in splits['train'])
    assert all(s.states[0].node_ids == ['10.0.0.1', '10.0.0.2'] for s in splits['train'])
    assert reports[0]['source_files'] == ['z_earlier.csv', 'a_later.csv']
    assert normalizer.constants['dtype'] == 'float32'


def test_split_windows_are_disjoint_and_training_stats_ignore_heldout_extremes():
    frame = events()
    frame.loc[70:, 'bytes_fwd'] = 1e9
    splits, normalizer, _ = prepare.prepare_frames([prepare.canonicalize(frame, 'all.csv')], CFG)
    node_bytes = NODE_FEATURE_NAMES.index('bytes_total')
    assert normalizer.constants['node']['mean'][node_bytes] == pytest.approx(10)
    train_windows = {s.metadata['window_start'] for sample in splits['train'] for s in sample.states}
    assert normalizer.constants['training_windows'] == len(train_windows)
    for left, right in [('train', 'val'), ('val', 'test')]:
        assert max(s.metadata['window_end'] for sample in splits[left] for s in sample.states) <= min(s.metadata['window_start'] for sample in splits[right] for s in sample.states)
    assert torch.isfinite(splits['test'][0].states[0].x).all()


def test_normalization_round_trip_construction_and_schema(tmp_path):
    frame = prepare.canonicalize(events(), 'events.csv')
    _, normalizer, _ = prepare.prepare_frames([frame], CFG)
    path = tmp_path / 'normalization.json'
    normalizer.save(path)
    loaded = FeatureNormalizer.load(path)
    state = build_graph_state(frame.iloc[:1], 'test', {'normalization_path': str(path)})
    raw = build_graph_state(frame.iloc[:1], 'test', {})
    assert torch.equal(state.x, loaded.transform(raw.x, 'node'))
    assert torch.equal(state.edge_attr, loaded.transform(raw.edge_attr, 'edge'))
    assert state.metadata['normalization_fingerprint'] == loaded.fingerprint
    assert state.x.dtype == torch.float32
    assert len(set(NODE_FEATURE_NAMES)) == len(NODE_FEATURE_NAMES)
    assert len(set(EDGE_FEATURE_NAMES)) == len(EDGE_FEATURE_NAMES)
    raw.metadata['split'] = 'test'
    with pytest.raises(ValueError, match='Only training'):
        FeatureNormalizer.fit([raw])


def test_secondary_corpora_cannot_enter_primary():
    for source in ['CTU-13', 'UNSW-NB15']:
        with pytest.raises(ValueError, match='Primary training'):
            prepare.prepare_frames([prepare.canonicalize(events(source=source), 'external.csv')], CFG)
    with pytest.raises(ValueError, match='requires primary'):
        prepare.prepare_frames([prepare.canonicalize(events(source='CTU-13'), 'heldout.csv')], CFG, purpose='heldout')


def test_missing_real_identity_or_time_is_rejected():
    frame = events()
    frame.loc[0, 'src'] = ''
    with pytest.raises(ValueError, match='endpoint'):
        prepare.canonicalize(frame, 'bad.csv')
    frame = events()
    frame.loc[0, 'timestamp'] = pd.NaT
    with pytest.raises(ValueError, match='timestamp'):
        prepare.canonicalize(frame, 'bad.csv')


def test_heldout_transform_preserves_training_constants():
    _, normalizer, _ = prepare.prepare_frames([prepare.canonicalize(events(), 'primary.csv')], CFG)
    fingerprint = normalizer.fingerprint
    splits, heldout_normalizer, _ = prepare.prepare_frames([prepare.canonicalize(events(source='CTU-13', volume=1e6), 'heldout.csv')], CFG, purpose='heldout', normalizer=normalizer)
    assert set(splits) == {'test'}
    assert heldout_normalizer.fingerprint == fingerprint
    assert splits['test'][0].states[0].metadata['normalization_fingerprint'] == fingerprint


def test_mixed_window_has_binary_infiltration_target():
    frame = events(2)
    frame.loc[1, 'label'] = 'PORTSCAN'
    state = build_graph_state(prepare.canonicalize(frame, 'mixed.csv'), 'env', {})
    assert state.y_infiltration == 1.0
    assert state.y_stage == 1


def test_benign_aliases_agree_with_stage_taxonomy():
    frame = events(4)
    frame['label'] = ['NORMAL', 'BACKGROUND', 'LEGITIMATE', '0']
    canonical = prepare.canonicalize(frame, 'benign.csv')
    assert canonical.infiltration.eq(0).all()
    assert canonical.stage.eq(0).all()


def test_adapter_keeps_distinct_environments_through_chaining():
    frame = events(4)
    frame['environment_id'] = ['lab-a', 'lab-a', 'lab-b', 'lab-b']
    converted = UnifiedAdapter('CIC-IDS2018')._convert_df(frame)
    chains = prepare.chain_environments([prepare.canonicalize(converted, 'combined.csv')])
    assert set(chains) == {'CIC-IDS2018::lab-a', 'CIC-IDS2018::lab-b'}


def test_adapter_preserves_host_ids_and_cic_calendar_dates():
    frame = events(3)
    frame['timestamp'] = ['02/03/2018 08:00:00', '2018-03-02 08:00:01', '14/02/2018 08:00:00']
    converted = UnifiedAdapter('CIC-IDS2018')._convert_df(frame)
    assert converted.src.tolist() == frame.src.tolist()
    assert converted.dst.tolist() == frame.dst.tolist()
    assert converted.timestamp.iloc[0] == pd.Timestamp('2018-03-02 08:00:00', tz='UTC')
    assert converted.timestamp.iloc[1] == pd.Timestamp('2018-03-02 08:00:01', tz='UTC')
    assert converted.timestamp.iloc[2] == pd.Timestamp('2018-02-14 08:00:00', tz='UTC')
