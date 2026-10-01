"""Run a predeclared remediation diagnostic on original inputs; never redefine gates."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import yaml

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--device',choices=['cpu','cuda'],default='cuda')
    p.add_argument('--lr',type=float,default=.001);p.add_argument('--class-balance',action='store_true')
    p.add_argument('--identity-normalization',action='store_true');p.add_argument('--frozen',action='store_true');args=p.parse_args()
    if args.frozen and args.identity_normalization:raise ValueError('Identity ablation is defined only for the original integration fixture.')
    folder=OUT/args.name
    if (folder/'config.yaml').exists():raise FileExistsError('Refuse to replace an existing experiment.')
    folder.mkdir(parents=True,exist_ok=True);os.chdir(ROOT)
    os.environ.update(OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONHASHSEED='42',PYTHONUTF8='1',
                     TEMP=str(ROOT/'.phase3-tmp'),TMP=str(ROOT/'.phase3-tmp'))
    if args.device=='cpu':os.environ['CUDA_VISIBLE_DEVICES']=''
    source='original_frozen_cuda' if args.frozen else 'original_cuda'
    cfg=yaml.safe_load((ROOT/f'examples/phase3_root_cause/{source}/config.yaml').read_text(encoding='utf-8'))
    cfg['train'].update(epochs=100,early_stopping_patience=101,lr=args.lr,
                        checkpoint=str(folder/'checkpoints/combined.pt'),history_path=str(folder/'train_history.json'))
    if args.class_balance:cfg['loss']['stage_class_balance']=True
    if args.identity_normalization:cfg['data']['processed_dir']=str(OUT/'identity_processed')
    path=folder/'config.yaml';path.write_text(yaml.safe_dump(cfg),encoding='utf-8')
    status=dict(name=args.name,device=args.device,epochs_requested=100,gate_unchanged=True,fixture=source,
                source_train_sha256=hashlib.sha256((ROOT/'scripts/train.py').read_bytes()).hexdigest(),commands=[])
    def run(label,command):
        started=time.monotonic();print('START',args.name,label,flush=True)
        with (folder/f'{label}.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,*command],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        status['commands'].append(dict(label=label,command=[sys.executable,*command],exit_code=result.returncode,seconds=time.monotonic()-started))
        (folder/'status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
        if result.returncode:raise RuntimeError(f'{label} failed; inspect its log')
    try:
        run('train',['scripts/phase3_train_measure.py','--config',str(path),'--device',args.device,'--measurement',str(folder/'memory.json')])
        import math
        history=json.loads((folder/'train_history.json').read_text())
        assert len(history)==100
        assert all(math.isfinite(v) for row in history for split in ('train','val') for v in row[split].values() if isinstance(v,(int,float)))
        status['epochs_completed']=len(history)
        for suffix in ('','_last'):
            run('rollout'+suffix,['examples/phase3_root_cause/inspect_rollouts.py','--checkpoint',str(folder/f'checkpoints/combined{suffix}.pt'),
                                  '--device',args.device,'--output',str(folder/f'rollout{suffix}.json')])
        selected=json.loads((folder/'rollout.json').read_text());last=json.loads((folder/'rollout_last.json').read_text())
        status.update(execution='complete',selected_epoch=selected['selected_epoch'],selected_all_steps_pass=selected['all_steps_pass'],
                      last_all_steps_pass=last['all_steps_pass'],selected_steps=selected['per_step'],last_steps=last['per_step'])
    except Exception as exc:
        status.update(execution='failed',error=str(exc));raise
    finally:
        (folder/'status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in status.items() if k not in ('commands','selected_steps','last_steps')}),flush=True)


if __name__=='__main__':main()
