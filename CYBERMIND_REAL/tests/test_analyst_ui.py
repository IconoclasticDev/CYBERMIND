import copy
from types import SimpleNamespace
import torch
from cybermind.analyst import view
from cybermind.analyst.view import compare_isolations, forecast_rows, network_dot
from cybermind.data.graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
from cybermind.data.types import GraphState
from cybermind.models.stage_decoder import StageDecoder


def state():
    return GraphState(torch.ones(2, 4), torch.tensor([[0,1],[1,0]]), torch.ones(2,4),
                      ['host"A', 'host B'], 10, 0, 0, 'case', 'Benign')


def test_forecast_steps_include_now_and_explicit_unknown_reset():
    decoder = StageDecoder()
    model = SimpleNamespace(use_crf_stage=True, stage_decoder=decoder)
    out = {'infiltration_probability': torch.tensor([.1,.2,.3,.4,.5]),
           'infiltration_variance': torch.tensor([0.,.01,.04,.09,.16]),
           'decoded_stages': torch.tensor([2,1,6,0,1]),
           'stage_reset_mask': torch.tensor([False,False,False,False,False])}
    rows = forecast_rows(out, model, 100, 5)
    assert len(rows) == 5 and rows[4]['timestamp'] == 120
    assert rows[0]['transition_legal'] is None
    assert rows[1]['transition_legal'] is False
    assert rows[2]['stage'] == 'Unknown/Ambiguous'
    assert rows[3]['transition_legal'] is True
    out['stage_reset_mask'][1] = True
    assert forecast_rows(out, model, 100, 5)[1]['transition_legal'] is True


def test_intervention_keeps_history_draws_and_input_immutable():
    calls = []
    class Model:
        def forecast(self, states, k, **kwargs):
            calls.append((copy.deepcopy(states), k, kwargs))
            return {'infiltration_probability': torch.tensor([float(states[-1].x.sum()/10)])}
    states = [state(), state()]
    before = copy.deepcopy(states)
    rows = compare_isolations(Model(), states, [0], 4, 8, 29)
    # A model using only node features should not respond to an edge-cut probe.
    assert all(row['risk_reduction'] == 0 for row in rows)
    assert len(calls) == 2
    assert all(len(c[0]) == 2 and c[2] == {'n_rollouts':8,'seed':29,'explain':False} for c in calls)
    assert torch.equal(calls[1][0][0].x, before[0].x)
    assert torch.equal(calls[1][0][-1].x, before[-1].x)
    assert calls[1][0][-1].edge_index.numel() == 0
    for actual, original in zip(states,before):
        assert torch.equal(actual.x, original.x)
        assert torch.equal(actual.edge_index, original.edge_index)


def test_network_escapes_labels_and_limits_nodes():
    dot = network_dot(state(), limit=1)
    assert 'host\\"A' in dot
    assert 'host B' not in dot and '0 -> 1' not in dot


def test_uploaded_csv_is_unlabeled_normalized_observed_history(tmp_path, monkeypatch):
    constants = {
        'version': 1, 'fit_split': 'train', 'dtype': 'float32', 'method': 'population_mean_std',
        'training_windows': 1,
        'node': {'features': NODE_FEATURE_NAMES, 'count': 1,
                 'mean': [0.] * len(NODE_FEATURE_NAMES), 'std': [1.] * len(NODE_FEATURE_NAMES)},
        'edge': {'features': EDGE_FEATURE_NAMES, 'count': 1,
                 'mean': [0.] * len(EDGE_FEATURE_NAMES), 'std': [1.] * len(EDGE_FEATURE_NAMES)},
    }
    cfg = {'data': {'window_seconds': 60, 'stride_seconds': 30, 'history': 2,
                    'require_packet_features': False, 'require_normalization': True}}
    checkpoint = {'node_dim': len(NODE_FEATURE_NAMES), 'normalization': constants,
                  'epoch': 1, 'config': cfg}
    model = object()
    monkeypatch.setattr(view, 'load_checkpoint', lambda path: (model, checkpoint, cfg))
    checkpoint_path = tmp_path / 'model.pt'
    checkpoint_path.write_bytes(b'trusted-test-placeholder')
    csv = tmp_path / 'capture.csv'
    csv.write_text(
        'Timestamp,Source IP,Destination IP,Source Port,Destination Port,Protocol,Label\n'
        '2026-01-01T00:00:00Z,10.0.0.1,10.0.0.2,1000,80,6,BENIGN\n'
        '2026-01-01T00:00:30Z,10.0.0.2,10.0.0.1,80,1000,6,ATTACK\n'
        '2026-01-01T00:01:00Z,10.0.0.1,10.0.0.3,1001,443,6,ATTACK\n', encoding='utf-8')
    loaded_model, loaded_cfg, sample, lineage, count = view.load_uploaded_case(checkpoint_path, csv)
    assert loaded_model is model and loaded_cfg is cfg and count >= 1
    assert len(sample.states) == 2
    assert all(item.attack_label == 'UNLABELED' for item in sample.states)
    assert all(item.y_infiltration == 0 for item in sample.states)
    assert lineage['split'] == 'live_upload_unlabeled'
    assert lineage['input_format'] == 'CSV'
