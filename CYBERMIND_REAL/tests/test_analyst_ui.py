import copy
from types import SimpleNamespace
import torch
from cybermind.analyst.view import compare_isolations, forecast_rows, network_dot
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
    assert rows[0]['risk_reduction'] > 0
    assert len(calls) == 2
    assert all(len(c[0]) == 2 and c[2] == {'n_rollouts':8,'seed':29,'explain':False} for c in calls)
    assert torch.equal(calls[1][0][0].x, before[0].x)
    for actual, original in zip(states,before):
        assert torch.equal(actual.x, original.x)
        assert torch.equal(actual.edge_index, original.edge_index)


def test_network_escapes_labels_and_limits_nodes():
    dot = network_dot(state(), limit=1)
    assert 'host\\"A' in dot
    assert 'host B' not in dot and '0 -> 1' not in dot
