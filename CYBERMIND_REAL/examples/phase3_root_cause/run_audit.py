"""Reproduce original fixtures; numerical controls are diagnostics, never new gates."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import yaml

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent


def main():
    os.chdir(ROOT)
    os.environ.update(OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONUTF8='1',PYTHONHASHSEED='42',
                     TEMP=str(ROOT/'.phase3-tmp'),TMP=str(ROOT/'.phase3-tmp'))
    records=[]
    def run(name,args,cpu=False):
        env=os.environ.copy()
        if cpu:env['CUDA_VISIBLE_DEVICES']=''
        start=time.monotonic(); print('START',name,flush=True)
        with (OUT/f'{name}.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,*args],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        records.append(dict(name=name,command=[sys.executable,*args],cpu_only=cpu,exit_code=result.returncode,seconds=time.monotonic()-start))
        (OUT/'commands.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        assert result.returncode==0,f'See {name}.log'
        print('PASS execution',name,flush=True)
    assert not (OUT/'commands.json').exists(),'Use a new directory rather than replacing an audit.'
    run('original_pipeline',['scripts/phase01_smoke.py','--use-edge-features','--use-crf-stage','--device','cpu',
                            '--output',str(OUT/'original_pipeline')],cpu=True)
    primary=yaml.safe_load((OUT/'original_pipeline/config.yaml').read_text())
    frozen=yaml.safe_load((ROOT/'examples/phase3_joint/smoke_combined_cuda/config.yaml').read_text())
    # Fixed before observing results: unchanged weight, NLL disabled, per-token
    # NLL scaling (original target length is 2), and the other original fixture.
    for name,source,weight in [('original_cuda',primary,.5),('crf_weight_zero',primary,0.),
                               ('crf_per_token',primary,.25),('original_frozen_cuda',frozen,.5)]:
        cfg=json.loads(json.dumps(source));folder=OUT/name;folder.mkdir(exist_ok=True)
        cfg['loss']['crf_stage']=weight
        cfg['train'].update(checkpoint=str(folder/'checkpoints/combined.pt'),history_path=str(folder/'train_history.json'))
        path=folder/'config.yaml';path.write_text(yaml.safe_dump(cfg),encoding='utf-8')
        run(name+'_train',['examples/phase3_root_cause/instrument_train.py','--config',str(path),'--device','cuda',
                          '--output',str(folder/'training_diagnostics.jsonl')])
        for suffix in ('','_last'):
            run(name+'_rollout'+suffix,['examples/phase3_root_cause/inspect_rollouts.py','--checkpoint',str(folder/f'checkpoints/combined{suffix}.pt'),
                 '--device','cuda','--output',str(folder/f'rollout{suffix}.json')])
    run('original_cpu_rollout',['examples/phase3_root_cause/inspect_rollouts.py','--checkpoint',
        str(OUT/'original_pipeline/checkpoints/original_pipeline.pt'),'--device','cpu','--output',str(OUT/'original_pipeline/rollout.json')],cpu=True)


if __name__=='__main__':main()
