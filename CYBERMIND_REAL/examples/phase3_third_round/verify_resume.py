"""Compare uninterrupted training with a real save/resume under the reviewed policy."""
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys
import torch
import yaml

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent/'resume_validation'


def main():
    os.chdir(ROOT)
    os.environ.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', CUDA_VISIBLE_DEVICES='', PYTHONUTF8='1',
                      TEMP=str(ROOT/'.phase3-tmp'), TMP=str(ROOT/'.phase3-tmp'))
    OUT.mkdir(exist_ok=True)
    cfg=yaml.safe_load((ROOT/'examples/phase3_third_round/extended200/config.yaml').read_text())
    cfg['train'].update(epochs=4,early_stopping_patience=10)
    for label in ('full','split'):
        folder=OUT/label;folder.mkdir(exist_ok=True)
        cfg['train'].update(checkpoint=str(folder/'checkpoints/model.pt'),history_path=str(folder/'history.json'))
        path=folder/'config.yaml'
        if path.exists():raise FileExistsError('Do not overwrite prior verification.')
        path.write_text(yaml.safe_dump(cfg),encoding='utf-8')
        def run(name,extra):
            with (folder/f'{name}.log').open('w',encoding='utf-8') as log:
                subprocess.run([sys.executable,'scripts/train.py','--config',str(path),'--device','cpu',*extra],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        if label=='full':run('train',[])
        else:
            run('first2',['--epochs','2'])
            run('resume',['--resume',str(folder/'checkpoints/model_last.pt')])
    spec=importlib.util.spec_from_file_location('parity',ROOT/'examples/phase2_stage_decoder/run_verification.py')
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    h.compare_legacy(json.loads((OUT/'split/history.json').read_text()),json.loads((OUT/'full/history.json').read_text()))
    result={'all_history_fields_match_within_1e_6':True,'checkpoints':{}}
    for name in ('model.pt','model_last.pt'):
        a=torch.load(OUT/f'full/checkpoints/{name}',weights_only=False,map_location='cpu')
        b=torch.load(OUT/f'split/checkpoints/{name}',weights_only=False,map_location='cpu')
        assert a['epoch']==b['epoch'] and a['selection_state']==b['selection_state']
        exact=all(torch.equal(v,b['model_state'][key]) for key,v in a['model_state'].items())
        assert exact
        result['checkpoints'][name]={'epoch':a['epoch'],'all_model_tensors_bitwise_equal':True,'selection_state_equal':True}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
