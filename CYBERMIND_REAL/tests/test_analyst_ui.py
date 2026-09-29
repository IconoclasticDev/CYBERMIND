import copy
from types import SimpleNamespace
import torch
from cybermind.analyst import view
from cybermind.analyst.view import compare_isolations, forecast_rows, network_dot
from cybermind.analyst.stage_evidence import analyze_stage_evidence, annotate_forecast_stage_coverage
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
    assert sample.metadata['observed_flow_rows']
    assert all(not row['review_flag'] for row in sample.metadata['observed_flow_rows'])


def test_stage_evidence_abstains_below_model_risk_gate():
    records = analyze_stage_evidence([state()], None, model_risk=.2)
    assert [record['stage_id'] for record in records] == [3, 4, 5]
    assert all(record['basis'] == 'abstention' for record in records)
    rows = [{'stage_id': 5, 'stage': 'Exfiltration'}]
    annotated = annotate_forecast_stage_coverage(rows, records)
    assert annotated[0]['model_stage'] == 'Exfiltration'
    assert annotated[0]['reported_stage'] == 'Unknown/Ambiguous'


def test_stage_evidence_reports_hosts_without_changing_model_output():
    first = GraphState(torch.tensor([[1., 1., 100., 1., 1., 1., 1., 0., 1., 1., 100., 1., .1, .2],
                                     [1., 1., 100., 1., 1., 1., 1., 0., 1., 1., 100., 1., .1, .2]]),
                       torch.tensor([[0], [1]]), torch.tensor([[100., 1., 6., 80., 1., 1., 1.]]),
                       ['10.0.0.1', '10.0.0.2'], 0, 0, 0, 'case', 'UNLABELED')
    second = GraphState(torch.tensor([[1., 3., 5_000_000., 3., 3., 3., 1., 0., 1., 1., 1_666_666., 1., .8, .9],
                                      [1., 1., 100., 1., 1., 1., 1., 0., 1., 1., 100., 1., .1, .2],
                                      [1., 1., 100., 1., 1., 1., 1., 0., 1., 1., 100., 1., .1, .2],
                                      [1., 1., 100., 1., 1., 1., 1., 0., 1., 1., 100., 1., .1, .2],
                                      [1., 1., 100., 1., 1., 1., 1., 0., 1., 1., 100., 1., .1, .2]]),
                        torch.tensor([[0, 0, 0, 0], [1, 2, 3, 4]]),
                        torch.tensor([[100., 1., 6., 445., 1., 1., 1.],
                                      [100., 1., 6., 445., 1., 1., 1.],
                                      [100., 1., 6., 445., 1., 1., 1.],
                                      [5_000_000., 100., 6., 443., 1., 1., 1.]]),
                        ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4', '8.8.8.8'],
                        30, 0, 0, 'case', 'UNLABELED')
    records = analyze_stage_evidence([first, second], None, model_risk=.9)
    by_stage = {record['stage_id']: record for record in records}
    assert by_stage[3]['status'] == 'rule-supported evidence'
    assert by_stage[5]['status'] == 'rule-supported evidence'
    assert by_stage[3]['hosts'][0]['host'] == '10.0.0.1'
    annotated = annotate_forecast_stage_coverage(
        [{'stage_id': 3, 'stage': 'Lateral Movement'}], records)
    assert annotated[0]['reported_stage'] == 'Lateral Movement'
    assert annotated[0]['model_stage'] == 'Lateral Movement'


def test_observed_flow_triage_uses_only_last_window_and_marks_telemetry_cues():
    import pandas as pd
    frame = pd.DataFrame([
        {'timestamp': pd.Timestamp('2026-01-01T00:00:00Z'), 'src': 'old', 'dst': 'x',
         'src_port': 1, 'dst_port': 2, 'protocol': 6, 'scan_unique_ports': 9,
         'scan_sequential_score': 1.0, 'retransmission_count': 0},
        {'timestamp': pd.Timestamp('2026-01-01T00:01:00Z'), 'src': 'new', 'dst': 'y',
         'src_port': 3, 'dst_port': 4, 'protocol': 6, 'scan_unique_ports': 5,
         'scan_sequential_score': .8, 'retransmission_count': 2},
    ])
    latest = state()
    latest.metadata = {'window_start': pd.Timestamp('2026-01-01T00:01:00Z').timestamp(),
                       'window_end': pd.Timestamp('2026-01-01T00:02:00Z').timestamp()}
    rows = view.observed_flow_rows(frame, latest)
    assert len(rows) == 1 and rows[0]['src'] == 'new'
    assert rows[0]['review_flag']
    assert rows[0]['review_signal'] == 'sequential port access, TCP retransmissions'


def test_replay_selects_only_histories_available_by_that_window(tmp_path, monkeypatch):
    from cybermind.data.graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
    constants = {
        'version': 1, 'fit_split': 'train', 'dtype': 'float32',
        'method': 'population_mean_std', 'training_windows': 1,
        'node': {'features': NODE_FEATURE_NAMES, 'count': 1,
                 'mean': [0.] * len(NODE_FEATURE_NAMES),
                 'std': [1.] * len(NODE_FEATURE_NAMES)},
        'edge': {'features': EDGE_FEATURE_NAMES, 'count': 1,
                 'mean': [0.] * len(EDGE_FEATURE_NAMES),
                 'std': [1.] * len(EDGE_FEATURE_NAMES)},
    }
    cfg = {'data': {'window_seconds': 60, 'stride_seconds': 30, 'history': 2,
                    'require_packet_features': False, 'require_normalization': True}}
    checkpoint = {'normalization': constants, 'epoch': 1, 'config': cfg}
    monkeypatch.setattr(view, 'load_checkpoint', lambda path: (object(), checkpoint, cfg))
    checkpoint_path = tmp_path / 'checkpoint.pt'
    checkpoint_path.write_bytes(b'test-checkpoint')
    csv = tmp_path / 'capture.csv'
    lines = ['Timestamp,Source IP,Destination IP,Source Port,Destination Port,Protocol']
    lines += [f'2026-01-01T00:{minute:02d}:00Z,10.0.0.1,10.0.0.2,1000,{80+minute},6'
              for minute in range(5)]
    csv.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    session = view.load_uploaded_session(checkpoint_path, csv)
    assert len(session[2]) >= 2
    _, _, early, early_lineage, count = view.select_uploaded_sequence(session, 0)
    _, _, late, late_lineage, _ = view.select_uploaded_sequence(session, count - 1)
    assert early.states[-1].timestamp < late.states[-1].timestamp
    assert early_lineage['sequence_index'] == 0
    assert late_lineage['sequence_index'] == count - 1
    assert all(row['timestamp'].timestamp() < early.states[-1].metadata['window_end']
               for row in early.metadata['observed_flow_rows'])
