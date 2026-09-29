#!/usr/bin/env python3
"""Offline Streamlit war-room UI. Requires a trained checkpoint for live forecasts."""
from pathlib import Path
import sys, json, torch
import streamlit as st
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.models.world_model import WorldModel

st.set_page_config(page_title='CYBERMIND War Room',layout='wide')
st.title('CYBERMIND — Predict → Simulate → Intervene → Replan')
ckpt_path=ROOT/'checkpoints/best_128gb.pt'
if not ckpt_path.exists():
    st.warning('No trained checkpoint found yet. Complete GPU training first.')
    st.stop()
ck=torch.load(ckpt_path,map_location='cpu',weights_only=False); cfg=ck['config']; node_dim=ck['node_dim']
m=WorldModel(node_dim,graph_hidden=cfg['model']['graph_hidden'],graph_out=cfg['model']['graph_out'],temporal_dim=cfg['model']['temporal_dim'],nhead=cfg['model']['nhead'],temporal_layers=cfg['model']['temporal_layers'],num_stages=cfg['model']['num_stages'],dropout=cfg['model']['dropout']); m.load_state_dict(ck['model_state']); m.eval()

ds=GraphSequenceDataset(ROOT/cfg['data']['processed_dir']/ 'test.pt')
idx=st.sidebar.number_input('Test sequence',0,max(0,len(ds)-1),0) if len(ds) else 0
if len(ds)==0: st.error('test.pt is empty'); st.stop()
sample=ds[int(idx)]
with torch.no_grad():
    out=m.forecast(sample.states[:-1],cfg['eval']['rollout_steps'])
    probs=torch.sigmoid(out['infiltration_logits']).cpu().numpy().tolist()
    stages=out['stage_logits'].argmax(-1).cpu().numpy().tolist()
cols=st.columns(4)
cols[0].metric('Current observed stage',str(sample.states[-2].y_stage))
cols[1].metric('Forecast risk (last rollout)',f'{100*probs[-1]:.1f}%')
cols[2].metric('Forecast stage',str(stages[-1]))
cols[3].metric('Rollout steps',str(len(probs)))
st.subheader('Future trajectory')
st.line_chart({'predicted_compromise_risk':probs})
st.caption('Risk is model output, not a causal probability. Use Counterfactual Risk Simulation for intervention comparisons.')
st.subheader('Current graph')
st.write({'nodes':sample.states[-2].node_ids,'edges':int(sample.states[-2].edge_index.shape[1])})
st.subheader('Prediction metadata')
st.json({'scenario':sample.scenario_id,'source':sample.metadata.get('source'),'attack_label':sample.states[-1].attack_label})
