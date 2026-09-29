#!/usr/bin/env python
from pathlib import Path
import argparse,json,sys
import numpy as np, torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.models.world_model import WorldModel
from cybermind.evaluation.metrics import binary_metrics,early_warning_lead_time
from cybermind.utils.config import load_config

def main():
    p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--checkpoint',required=True); p.add_argument('--split',default='test'); p.add_argument('--threshold',type=float,default=.5); args=p.parse_args(); cfg=load_config(args.config)
    root=Path(__file__).resolve().parents[1]; ds=GraphSequenceDataset(root/cfg['data']['processed_dir']/f'{args.split}.pt'); ck=torch.load(root/args.checkpoint,map_location='cpu',weights_only=False)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'); node_dim=ck['node_dim']; m=WorldModel(node_dim,graph_hidden=cfg['model']['graph_hidden'],graph_out=cfg['model']['graph_out'],temporal_dim=cfg['model']['temporal_dim'],nhead=cfg['model']['nhead'],temporal_layers=cfg['model']['temporal_layers'],num_stages=cfg['model']['num_stages'],dropout=cfg['model']['dropout']).to(device); m.load_state_dict(ck['model_state']); m.eval()
    all_y=[]; all_p=[]; per=[]
    for sample in ds:
        states=sample.states
        for s in states: s.x=s.x.to(device); s.edge_index=s.edge_index.to(device); s.edge_attr=s.edge_attr.to(device)
        with torch.no_grad():
            out=m.forecast(states[:-1],cfg['eval']['rollout_steps']); p=float(torch.sigmoid(out['infiltration_logits'][-1]).item())
        y=float(states[-1].y_infiltration); all_y.append(y); all_p.append(p)
        ts=np.array([s.timestamp for s in states]); yy=np.array([s.y_infiltration for s in states]);
        hist=[float(torch.sigmoid(m.infiltration_head(m.forward(states[:i+1])['temporal_latents'][-1])).item()) for i in range(max(1,len(states)-1))]
        per.append({'scenario':sample.scenario_id,'target':y,'predicted_future_risk':p,**early_warning_lead_time(ts,yy,np.pad(np.array(hist), (0,max(0,len(ts)-len(hist))))[:len(ts)],args.threshold)})
    metrics=binary_metrics(all_y,all_p,args.threshold); metrics['mean_lead_time_seconds']=float(np.mean([x['lead_time_seconds'] for x in per if x['lead_time_seconds'] is not None])) if any(x['lead_time_seconds'] is not None for x in per) else None
    result={'split':args.split,'metrics':metrics,'per_sample':per}
    (root/'results').mkdir(exist_ok=True); (root/'results'/f'eval_{args.split}.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
