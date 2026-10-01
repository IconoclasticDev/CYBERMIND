#!/usr/bin/env python
from pathlib import Path
import argparse,sys,torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cybermind.data.types import GraphState,GraphSequenceSample
from cybermind.data.dataset import save_dataset

def build(n=24,node_dim=14,seq=8):
 out=[]
 for i in range(n):
  states=[]
  for t in range(seq):
   nodes=8+(i%4); x=torch.rand(nodes,node_dim); edge=torch.combinations(torch.arange(nodes),r=2).t().contiguous(); attr=torch.rand(edge.size(1),7)
   attack=1.0 if (i%3==0 and t>=seq//2) else 0.; stage=5 if attack and t>=seq-2 else (2 if attack else 0)
   states.append(GraphState(x,edge,attr,[f'H{j}' for j in range(nodes)],float(t),attack,stage,f'S{i}','BENIGN' if not attack else 'SYNTH_ATTACK'))
  out.append(GraphSequenceSample(states,f'S{i}',0,60.0,{}))
 return out
p=argparse.ArgumentParser(); p.add_argument('--out',default='data/processed'); args=p.parse_args(); root=Path(__file__).resolve().parents[1]; out=root/args.out; out.mkdir(parents=True,exist_ok=True); samples=build(); save_dataset(samples[:18],out/'train.pt'); save_dataset(samples[18:21],out/'val.pt'); save_dataset(samples[21:],out/'test.pt'); print('generated',len(samples))
