"""CRF loss and inference wiring, independent of Phase 3 feature ablations."""
from dataclasses import replace
from pathlib import Path
import importlib.util
import sys

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.data.types import GraphState, GraphSequenceSample
from cybermind.evaluation.metrics import illegal_transition_rate
from cybermind.models.world_model import WorldModel
from cybermind.utils.config import stage_model_kwargs

spec = importlib.util.spec_from_file_location('stage_integration_train', ROOT / 'scripts/train.py')
train = importlib.util.module_from_spec(spec)
spec.loader.exec_module(train)


def tiny_model(enabled=True, device='cpu'):
    torch.manual_seed(911)
    return WorldModel(4,graph_hidden=8,graph_out=8,temporal_dim=8,nhead=2,
                      temporal_layers=1,graph_heads=2,dropout=0.,use_crf_stage=enabled).to(device)


def sequences():
    generator=torch.Generator().manual_seed(16)
    return [GraphSequenceSample([GraphState(
        x=torch.randn(3,4,generator=generator),edge_index=torch.tensor([[0,1,2],[1,2,0]]),
        edge_attr=torch.zeros(3,7),node_ids=['a','b','c'],timestamp=float(t),
        y_infiltration=float(i==1 and t>0),y_stage=t if i==1 else 0,
        scenario_id=str(i),attack_label='synthetic') for t in range(4)],str(i),0.,1.) for i in range(2)]


@pytest.mark.parametrize('device',['cpu','cuda'])
def test_crf_training_gradient_and_forecast_integration(device,record_property):
    if device=='cuda' and not torch.cuda.is_available():
        pytest.skip('Actual CUDA required for Phase 2 exit evidence')
    torch.set_num_threads(1)
    model=tiny_model(device=device)
    batch=sequences()
    cfg={'model':{'num_stages':7},'loss':{'transition':1.,'infiltration':1.,'stage':.5,
          'crf_stage':.5,'calibration':.2,'graph_consistency':.1,'use_crf_stage':True}}
    loss,parts=train.batch_loss(model,batch,cfg,torch.device(device))
    assert torch.isfinite(loss) and parts['crf_stage']>0
    loss.backward()
    gradient=model.stage_decoder.transitions.grad
    assert gradient is not None and torch.isfinite(gradient).all() and gradient.norm()>0
    assert torch.count_nonzero(gradient[~model.stage_decoder.allowed_transitions])==0
    head_gradient=model.stage_head.net[-1].weight.grad
    assert head_gradient is not None and torch.isfinite(head_gradient).all() and head_gradient.norm()>0
    states=[replace(s,x=s.x.to(device),edge_index=s.edge_index.to(device),edge_attr=s.edge_attr.to(device))
            for s in batch[0].states]
    with torch.no_grad():
        forecast=model.forecast(states,k=4,n_rollouts=3,explain=False)
    assert forecast['decoded_stages'].shape==(5,)
    assert forecast['stage_decoding']=='crf_viterbi'
    assert illegal_transition_rate(forecast['decoded_stages'])==0
    with torch.no_grad():
        rollout=model.rollout_from_latent(torch.zeros(2,8,device=device),3)
    assert rollout['decoded_stages'].shape==(4,2)
    assert illegal_transition_rate(rollout['decoded_stages'].T)==0
    record_property('device',device)
    record_property('joint_loss',float(loss.detach()))
    record_property('crf_loss',parts['crf_stage'])
    record_property('transition_gradient_norm',float(gradient.norm()))
    record_property('forecast_illegal_transition_rate',0.0)


def test_crf_off_preserves_parameters_and_plain_argmax():
    off=tiny_model(False)
    on=tiny_model(True)
    for key,value in off.state_dict().items():
        assert torch.equal(value,on.state_dict()[key]),key
    assert not any('stage_decoder' in key for key in off.state_dict())
    emissions=torch.randn(2,4,7)
    assert torch.equal(off.decode_stages(emissions),emissions.argmax(-1))
    with torch.no_grad():
        out=off.forecast(sequences()[0].states,k=2,n_rollouts=3,explain=False)
    assert torch.equal(out['decoded_stages'],out['stage_logits'].argmax(-1))


def test_training_reset_metadata_is_explicit_and_cannot_hide_other_jumps():
    model=tiny_model(True)
    batch=sequences()
    # Target subsequence [3,0,1] needs an explicitly declared reset at target 0.
    for state,label in zip(batch[1].states[1:],[3,0,1]):
        state.y_stage=label
    cfg={'model':{'num_stages':7},'loss':{'use_crf_stage':True,'stage':.5}}
    with pytest.raises(ValueError,match='illegal target'):
        train.batch_loss(model,batch,cfg,torch.device('cpu'))
    batch[1].states[2].metadata['campaign_reset']=True
    assert torch.isfinite(train.batch_loss(model,batch,cfg,torch.device('cpu'))[0])
    batch[1].states[2].y_stage=2
    with pytest.raises(ValueError,match='illegal target'):
        train.batch_loss(model,batch,cfg,torch.device('cpu'))


def test_training_exclusion_changes_only_crf_component_and_requires_opt_in(monkeypatch):
    model=tiny_model(True)
    model.eval()
    batch=sequences()
    for state,label in zip(batch[1].states[1:],[1,2,0]):
        state.y_stage=label
    batch[1].states[3].metadata['crf_transition_loss_excluded']=True
    observed={}
    original_stage_ce=train.stage_cross_entropy
    def capture_stage_ce(logits,target,cfg):
        observed['target']=target.detach().clone()
        observed['rows']=len(logits)
        return original_stage_ce(logits,target,cfg)
    monkeypatch.setattr(train,'stage_cross_entropy',capture_stage_ce)
    base={'model':{'num_stages':7},'loss':{'use_crf_stage':True,'stage':.5}}
    with pytest.raises(ValueError,match='reviewed config'):
        train.batch_loss(model,batch,base,torch.device('cpu'))
    enabled={'model':{'num_stages':7},'loss':{
        'use_crf_stage':True,'use_crf_transition_exclusions':True,'stage':.5}}
    loss,parts=train.batch_loss(model,batch,enabled,torch.device('cpu'))
    assert torch.isfinite(loss) and parts['crf_stage']>0 and parts['stage']>0
    assert observed['rows']==6 and observed['target'].tolist()[-3:]==[1,2,0]
    batch[1].states[3].metadata.pop('crf_transition_loss_excluded')
    with pytest.raises(ValueError,match='illegal target'):
        train.batch_loss(model,batch,enabled,torch.device('cpu'))


def test_crf_checkpoint_config_resolution():
    saved={'loss':{'use_crf_stage':True}}
    assert stage_model_kwargs({},saved)=={'use_crf_stage':True}
    assert stage_model_kwargs({})=={'use_crf_stage':False}
    with pytest.raises(ValueError):
        stage_model_kwargs({'loss':{'use_crf_stage':False}},saved)
    with pytest.raises(ValueError):
        stage_model_kwargs({'loss':{'use_crf_stage':'false'}})


def test_crf_forecast_explanations_work_under_inference_mode():
    model=tiny_model(True)
    with torch.inference_mode():
        out=model.forecast(sequences()[0].states,k=1,n_rollouts=3)
    assert out['explanation']['feature_occlusion']
    assert illegal_transition_rate(out['decoded_stages'])==0
