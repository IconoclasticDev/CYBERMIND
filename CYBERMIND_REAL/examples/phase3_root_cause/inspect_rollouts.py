"""Log original-fixture emissions/transitions and gate each forecast step separately."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from cybermind.models.world_model import WorldModel
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.utils.config import edge_model_kwargs,stage_model_kwargs


def main():
    p=argparse.ArgumentParser(); p.add_argument('--checkpoint',required=True);p.add_argument('--output',required=True)
    p.add_argument('--device',default='cuda');args=p.parse_args()
    torch.set_num_threads(2)
    ck=torch.load(args.checkpoint,map_location='cpu',weights_only=False);cfg=ck['config']
    assert cfg['eval']['rollout_steps']==4
    options={k:cfg['model'][k] for k in ('graph_hidden','graph_out','temporal_dim','nhead','temporal_layers','num_stages','dropout')}
    options['graph_heads']=cfg['model'].get('graph_heads',8)
    model=WorldModel(ck['node_dim'],**options,**edge_model_kwargs(cfg['model']),**stage_model_kwargs(cfg)).to(args.device).eval()
    model.load_state_dict(ck['model_state'])
    dataset=GraphSequenceDataset(ROOT/cfg['data']['processed_dir']/'test.pt')
    rows=[]; saved=model.stage_decoder.transitions.detach().clone()
    allowed=model.stage_decoder.allowed_transitions
    for sample in dataset:
        states=sample.states[:-1]
        for s in states: s.x=s.x.to(args.device);s.edge_index=s.edge_index.to(args.device);s.edge_attr=s.edge_attr.to(args.device)
        captured=[]
        hook=model.stage_head.register_forward_hook(lambda _m,_i,output:captured.append(output.detach().clone()))
        with torch.no_grad():
            result=model.forecast(states,4,n_rollouts=cfg['eval'].get('n_rollouts',16),seed=cfg['eval'].get('rollout_seed',0),explain=False)
        hook.remove()
        assert len(captured)==1
        raw=captured[0].float();emissions=raw.mean(dim=1)
        decoded=result['decoded_stages']
        # Controlled diagnostic only: keep all hard masks, zero learned scores.
        with torch.no_grad():
            model.stage_decoder.transitions.zero_()
            zero_path=model.stage_decoder.decode(emissions)
            model.stage_decoder.transitions.copy_(saved)
        steps=[]
        for t in range(5):
            logits=emissions[t];prob=logits.softmax(-1);top=logits.topk(2).values
            steps.append(dict(step=t,emission_logits=logits.cpu().tolist(),raw_argmax=int(logits.argmax()),
                decoded_stage=int(decoded[t]),zero_learned_transition_stage=int(zero_path[t]),
                emission_margin=float(top[0]-top[1]),normalized_entropy=float(-(prob*prob.log()).sum()/torch.log(torch.tensor(7.,device=prob.device))),
                transition_matrix=saved.cpu().tolist(),
                masked_transition_matrix=[[float(saved[i,j]) if bool(allowed[i,j]) else '-inf' for j in range(7)] for i in range(7)],
                incoming_illegal=False if t==0 else not bool(allowed[decoded[t-1],decoded[t]])))
        rows.append(dict(scenario=sample.scenario_id,observed_timestamps=[s.timestamp for s in states],
                         steps=steps,per_trajectory_emissions=raw.cpu().tolist(),
                         latent_step_zero=result['latent'][0].cpu().tolist()))
    summary=[]
    for t in range(1,5):
        subset=[r['steps'][t] for r in rows]
        stages=[r['decoded_stage'] for r in subset];raw_stages=[r['raw_argmax'] for r in subset]
        zero=[r['zero_learned_transition_stage'] for r in subset]
        values=torch.tensor([r['emission_logits'] for r in subset])
        known=len(set(stages)-{6});unknown=stages.count(6);illegal=sum(r['incoming_illegal'] for r in subset)
        summary.append(dict(step=t,samples=len(stages),distinct_non_unknown=known,unknown_count=unknown,
            illegal_count=illegal,decoded_histogram=dict(Counter(stages)),raw_argmax_histogram=dict(Counter(raw_stages)),
            zero_transition_histogram=dict(Counter(zero)),mean_logits=values.mean(0).tolist(),
            max_across_sample_logit_std=float(values.std(0,unbiased=False).max()),
            mean_margin=sum(r['emission_margin'] for r in subset)/len(subset),
            mean_normalized_entropy=sum(r['normalized_entropy'] for r in subset)/len(subset),
            passed=known>=2 and unknown<len(stages) and illegal==0))
    forward=[float(saved[i,j]) for i in range(6) for j in range(i+1,6)]
    stay=[float(saved[i,i]) for i in range(6)]
    report=dict(checkpoint=str(args.checkpoint),selected_epoch=ck['epoch'],selection_metric=ck['selection_metric'],
                device=args.device,rollout_steps=4,hard_masks_unchanged=True,declared_forecast_resets=False,
                transition_summary=dict(stay_min=min(stay),stay_max=max(stay),forward_min=min(forward),forward_max=max(forward),
                                        max_absolute=float(saved.abs().max())),
                per_step=summary,all_steps_pass=all(s['passed'] for s in summary),samples=rows)
    Path(args.output).write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))


if __name__=='__main__':main()
