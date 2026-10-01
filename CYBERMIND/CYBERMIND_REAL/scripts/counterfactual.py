#!/usr/bin/env python
from pathlib import Path
import argparse,json,sys,torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.models.world_model import WorldModel
from cybermind.counterfactual.simulator import rank_interventions,attack_gravity
from cybermind.utils.config import load_config, edge_model_kwargs, stage_model_kwargs
from cybermind.utils.inference import verify_inference_states

a=argparse.ArgumentParser(); a.add_argument('--config',required=True); a.add_argument('--checkpoint',required=True); a.add_argument('--split',default='test'); a.add_argument('--index',type=int,default=0); args=a.parse_args(); cfg=load_config(args.config); root=Path(__file__).resolve().parents[1]
ds=GraphSequenceDataset(root/cfg['data']['processed_dir']/f'{args.split}.pt'); ck=torch.load(root/args.checkpoint,map_location='cpu',weights_only=False); m=WorldModel(ck['node_dim'],graph_hidden=cfg['model']['graph_hidden'],graph_out=cfg['model']['graph_out'],temporal_dim=cfg['model']['temporal_dim'],nhead=cfg['model']['nhead'],temporal_layers=cfg['model']['temporal_layers'],num_stages=cfg['model']['num_stages'],dropout=cfg['model']['dropout'],graph_heads=cfg['model'].get('graph_heads',8),**edge_model_kwargs(cfg['model'],ck['config']['model']),**stage_model_kwargs(cfg,ck['config'])); m.load_state_dict(ck['model_state']); s=ds[args.index].states[-1];
with torch.no_grad():
    verify_inference_states(ck,[s])
    prediction=m.forecast([s],cfg['eval']['rollout_steps'],
                         n_rollouts=cfg['eval'].get('n_rollouts',16),seed=cfg['eval'].get('rollout_seed',0))
print('Prediction explanation:',json.dumps(prediction['explanation'],indent=2))
print('Attack Gravity:',json.dumps(attack_gravity(m,s,k=cfg['eval']['rollout_steps']),indent=2)); print('Interventions:',json.dumps(rank_interventions(m,s,k=cfg['eval']['rollout_steps']),indent=2))
