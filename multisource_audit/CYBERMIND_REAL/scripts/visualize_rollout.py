#!/usr/bin/env python
from pathlib import Path
import argparse,sys
import matplotlib.pyplot as plt
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.models.world_model import WorldModel
from cybermind.utils.config import load_config

def main():
 p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--checkpoint',required=True); p.add_argument('--split',default='test'); p.add_argument('--index',type=int,default=0); args=p.parse_args(); cfg=load_config(args.config); root=Path(__file__).resolve().parents[1]
 ds=GraphSequenceDataset(root/cfg['data']['processed_dir']/f'{args.split}.pt'); ck=torch.load(root/args.checkpoint,map_location='cpu',weights_only=False); node_dim=ck['node_dim']
 m=WorldModel(node_dim,graph_hidden=cfg['model']['graph_hidden'],graph_out=cfg['model']['graph_out'],temporal_dim=cfg['model']['temporal_dim'],nhead=cfg['model']['nhead'],temporal_layers=cfg['model']['temporal_layers'],num_stages=cfg['model']['num_stages'],dropout=cfg['model']['dropout']); m.load_state_dict(ck['model_state']); m.eval()
 sample=ds[args.index];
 with torch.no_grad(): out=m.forecast(sample.states[:-1],cfg['eval']['rollout_steps']); risks=torch.sigmoid(out['infiltration_logits']).flatten().numpy()
 plt.figure(figsize=(10,5)); plt.plot(range(len(risks)),risks,marker='o',label='Predicted future infiltration risk'); plt.ylim(0,1); plt.xlabel('Rollout step'); plt.ylabel('Probability'); plt.title(f'CYBERMIND K-step rollout — {sample.scenario_id}'); plt.grid(True,alpha=.2); plt.legend(); plt.tight_layout(); outp=root/'results'/'rollout.png'; plt.savefig(outp,dpi=180); print(outp)
if __name__=='__main__': main()
