#!/usr/bin/env python
from pathlib import Path
import argparse,json,sys
import numpy as np, torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.models.world_model import WorldModel
from cybermind.evaluation.metrics import binary_metrics,early_warning_lead_time
from cybermind.utils.config import load_config
from cybermind.utils.inference import verify_inference_states

def main():
    p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--checkpoint',required=True); p.add_argument('--split',default='test'); p.add_argument('--threshold',type=float,default=.5); p.add_argument('--output',help='Report path; defaults to results/eval_SPLIT.json'); args=p.parse_args(); cfg=load_config(args.config)
    root=Path(__file__).resolve().parents[1]; ds=GraphSequenceDataset(root/cfg['data']['processed_dir']/f'{args.split}.pt'); ck=torch.load(root/args.checkpoint,map_location='cpu',weights_only=False)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'); node_dim=ck['node_dim']; m=WorldModel(node_dim,graph_hidden=cfg['model']['graph_hidden'],graph_out=cfg['model']['graph_out'],temporal_dim=cfg['model']['temporal_dim'],nhead=cfg['model']['nhead'],temporal_layers=cfg['model']['temporal_layers'],num_stages=cfg['model']['num_stages'],dropout=cfg['model']['dropout'],graph_heads=cfg['model'].get('graph_heads',8)).to(device); m.load_state_dict(ck['model_state']); m.eval()
    all_y=[]; all_p=[]; per=[]
    for sample in ds:
        states=sample.states
        verify_inference_states(ck,states)
        for s in states: s.x=s.x.to(device); s.edge_index=s.edge_index.to(device); s.edge_attr=s.edge_attr.to(device)
        with torch.no_grad():
            # Each sample holds one unseen target window, so evaluate one step ahead.
            out=m.forecast(states[:-1],1,
                           n_rollouts=cfg['eval'].get('n_rollouts',16),seed=cfg['eval'].get('rollout_seed',0))
            p=float(out['infiltration_probability'][-1].item())
        y=float(states[-1].y_infiltration); all_y.append(y); all_p.append(p)
        ts=np.array([s.timestamp for s in states]); yy=np.array([s.y_infiltration for s in states]);
        with torch.no_grad():
            hist=[float(torch.sigmoid(m.infiltration_head(m.forward(states[:i+1])['temporal_latents'][-1])).item()) for i in range(max(1,len(states)-1))]
        per.append({'scenario':sample.scenario_id,'target':y,'predicted_future_risk':p,
                    'predictive_variance':float(out['infiltration_variance'][-1].item()),
                    'explanation':out['explanation'],
                    **early_warning_lead_time(ts,yy,np.pad(np.array(hist), (0,max(0,len(ts)-len(hist))))[:len(ts)],args.threshold)})
    metrics=binary_metrics(all_y,all_p,args.threshold); metrics['mean_lead_time_seconds']=float(np.mean([x['lead_time_seconds'] for x in per if x['lead_time_seconds'] is not None])) if any(x['lead_time_seconds'] is not None for x in per) else None
    result={'split':args.split,'forecast_horizon_windows':1,'metrics':metrics,'per_sample':per}
    output=root/args.output if args.output else root/'results'/f'eval_{args.split}.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
