#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys
import torch
from torch.optim import AdamW
from torch.utils.data import DataLoader
from tqdm import tqdm
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cybermind.data.dataset import GraphSequenceDataset,collate_identity
from cybermind.models.world_model import WorldModel
from cybermind.losses import gaussian_transition_loss,infiltration_loss,stage_loss,binary_brier
from cybermind.utils.config import load_config
from cybermind.utils.repro import seed_everything

def batch_loss(model,batch,cfg,device):
    states=[]
    for sample in batch:
        ss=[]
        for s in sample.states:
            s.x=s.x.to(device,non_blocking=True); s.edge_index=s.edge_index.to(device,non_blocking=True); s.edge_attr=s.edge_attr.to(device,non_blocking=True); ss.append(s)
        states.append(ss)
    enc=model.forward_batch(states); z=enc['temporal_latents']
    pred=model.dynamics(z[:,:-1]); true=z[:,1:].detach()
    l_trans=gaussian_transition_loss(pred.reshape(-1,pred.size(-1)),true.reshape(-1,true.size(-1)))
    risk_logits=model.infiltration_head(pred).reshape(-1); risk_y=torch.tensor([st.y_infiltration for ss in states for st in ss[1:]],dtype=torch.float32,device=device)
    l_infil=infiltration_loss(risk_logits,risk_y); l_brier=binary_brier(risk_logits,risk_y)
    stage_logits=model.stage_head(pred).reshape(-1,cfg['model']['num_stages']); stage_y=torch.tensor([st.y_stage for ss in states for st in ss[1:]],dtype=torch.long,device=device).clamp(0,cfg['model']['num_stages']-1)
    l_stage=stage_loss(stage_logits,stage_y)
    total=cfg['loss']['transition']*l_trans+cfg['loss']['infiltration']*l_infil+cfg['loss']['stage']*l_stage+cfg['loss']['calibration']*l_brier
    return total, {'transition':l_trans.item(),'infiltration':l_infil.item(),'stage':l_stage.item(),'brier':l_brier.item()}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--resume'); p.add_argument('--epochs',type=int,default=0); args=p.parse_args(); cfg=load_config(args.config); seed_everything(cfg.get('seed',42))
    root=Path(__file__).resolve().parents[1]; device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'); print('device',device)
    if device.type!='cuda': print('WARNING: running on CPU; production training should use CUDA.')
    train=GraphSequenceDataset(root/cfg['data']['processed_dir']/ 'train.pt'); val_path=root/cfg['data']['processed_dir']/ 'val.pt'; val=GraphSequenceDataset(val_path) if val_path.exists() else None
    if len(train)==0: raise RuntimeError('Empty training set.')
    node_dim=train[0].states[0].x.size(1)
    m=WorldModel(node_dim,graph_hidden=cfg['model']['graph_hidden'],graph_out=cfg['model']['graph_out'],temporal_dim=cfg['model']['temporal_dim'],nhead=cfg['model']['nhead'],temporal_layers=cfg['model']['temporal_layers'],num_stages=cfg['model']['num_stages'],dropout=cfg['model']['dropout']).to(device)
    opt=AdamW(m.parameters(),lr=cfg['train']['lr'],weight_decay=cfg['train']['weight_decay'])
    scaler=torch.amp.GradScaler('cuda',enabled=device.type=='cuda')
    bs=int(cfg['train'].get('batch_size',1)); accum=int(cfg['train'].get('grad_accumulation',1)); loader=DataLoader(train,batch_size=bs,shuffle=True,collate_fn=collate_identity,num_workers=int(cfg['train'].get('num_workers',0)),pin_memory=device.type=='cuda')
    start_epoch=0
    if args.resume:
        ck=torch.load(args.resume,map_location='cpu',weights_only=False); m.load_state_dict(ck['model_state']); opt.load_state_dict(ck.get('optimizer_state',opt.state_dict())); start_epoch=int(ck.get('epoch',0)); print('resumed',args.resume,'epoch',start_epoch)
    best=float('inf'); history=[]; ckpt_name=cfg['train']['checkpoint']
    epochs = int(args.epochs) if args.epochs > 0 else int(cfg['train']['epochs'])
    for ep in range(start_epoch,epochs):
        m.train(); running=0.; comps={}; opt.zero_grad(set_to_none=True)
        for step,batch in enumerate(tqdm(loader,desc=f'epoch {ep+1}')):
            with torch.amp.autocast('cuda',enabled=device.type=='cuda'):
                loss,parts=batch_loss(m,batch,cfg,device); loss=loss/accum
            scaler.scale(loss).backward()
            if (step+1)%accum==0 or (step+1)==len(loader):
                scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(m.parameters(),cfg['train']['grad_clip']); scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True)
            running += loss.item()*accum
            for k,v in parts.items(): comps[k]=comps.get(k,0)+v
        mean=running/max(len(loader),1); rec={'epoch':ep+1,'loss':mean,**{k:v/max(len(loader),1) for k,v in comps.items()}}; history.append(rec); print(rec)
        # Best checkpoint is training-loss based; final evaluation remains separate and leakage-free.
        if mean<best:
            best=mean; (root/'checkpoints').mkdir(exist_ok=True); torch.save({'model_state':m.state_dict(),'optimizer_state':opt.state_dict(),'config':cfg,'node_dim':node_dim,'epoch':ep+1,'best_loss':best},root/'checkpoints'/ckpt_name)
    (root/'results').mkdir(exist_ok=True); (root/'results'/'train_history.json').write_text(json.dumps(history,indent=2)); print('saved',root/'checkpoints'/ckpt_name)

if __name__=='__main__': main()
