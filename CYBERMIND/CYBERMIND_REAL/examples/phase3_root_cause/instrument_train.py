"""Instrument the unchanged active train.py; diagnostic records do not alter loss."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))


def main():
    p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--output',required=True)
    p.add_argument('--device',default='cuda'); args=p.parse_args()
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    spec=importlib.util.spec_from_file_location('audited_train',ROOT/'scripts/train.py')
    train=importlib.util.module_from_spec(spec); spec.loader.exec_module(train)
    original=train.batch_loss
    counter=0
    def batch_loss(model,batch,cfg,device,**kwargs):
        nonlocal counter
        if not model.training:
            return original(model,batch,cfg,device,**kwargs)
        captured=[]
        hook=model.stage_head.register_forward_hook(lambda _m,_i,output: captured.append(output))
        try:
            result=original(model,batch,cfg,device,**kwargs)
        finally:
            hook.remove()
        emissions=captured[0]
        labels=torch.tensor([[s.y_stage for s in sample.states[1:]] for sample in batch],device=device)
        resets=torch.tensor([[s.metadata.get('campaign_reset',False) for s in sample.states[1:]] for sample in batch],device=device,dtype=torch.bool)
        ce=torch.nn.functional.cross_entropy(emissions.reshape(-1,7).float(),labels.flatten())
        nll=model.stage_decoder(emissions.float(),labels,reset_mask=resets)
        ce_weight=cfg['loss']['stage']; crf_weight=cfg['loss'].get('crf_stage',ce_weight)
        # autograd.grad returns diagnostics without writing parameter .grad.
        parameters=(emissions,model.stage_head.net[-1].weight,model.to_latent.weight)
        cg=torch.autograd.grad(ce_weight*ce,parameters,retain_graph=True,allow_unused=True)
        ng=torch.autograd.grad(crf_weight*nll,parameters,retain_graph=True,allow_unused=True)
        grads={}
        for name,a,b in zip(('emissions','stage_head_weight','upstream_to_latent_weight'),cg,ng):
            if a is None or b is None:
                grads[name]=None; continue
            an=float(a.norm()); bn=float(b.norm())
            grads[name]=dict(ce_norm=an,crf_norm=bn,crf_to_ce_ratio=bn/max(an,1e-30),
                            cosine=float(torch.nn.functional.cosine_similarity(a.flatten(),b.flatten(),dim=0)))
        counter+=1
        row=dict(training_batch=counter,sequence_target_steps=labels.shape[1],batch_size=len(batch),
                 stage_ce=float(ce.detach()),crf_nll=float(nll.detach()),ce_weight=ce_weight,crf_weight=crf_weight,
                 weighted_ce=float((ce_weight*ce).detach()),weighted_crf=float((crf_weight*nll).detach()),
                 total_loss=float(result[0].detach()),gradients=grads,
                 transitions_before_optimizer_update=model.stage_decoder.transitions.detach().cpu().tolist(),
                 emission_logits_before_crf=emissions.detach().cpu().tolist(),
                 emission_argmax=emissions.detach().argmax(-1).cpu().tolist(),labels=labels.cpu().tolist())
        with out.open('a',encoding='utf-8') as f: f.write(json.dumps(row,allow_nan=False)+'\n')
        return result
    train.batch_loss=batch_loss
    assert not out.exists(), 'Refuse to overwrite training diagnostics.'
    sys.argv=['train.py','--config',args.config,'--device',args.device]
    train.main()


if __name__=='__main__': main()
