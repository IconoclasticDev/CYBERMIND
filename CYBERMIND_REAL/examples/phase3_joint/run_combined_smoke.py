"""Two-epoch CUDA run of configs/smoke.yaml with both features, frozen input only."""
from pathlib import Path
import json
import math
import os
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'smoke_combined_cuda'


def main():
    OUT.mkdir(exist_ok=True)
    os.chdir(ROOT)
    os.environ.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONUTF8='1',
                     TEMP=str(ROOT / '.phase3-tmp'), TMP=str(ROOT / '.phase3-tmp'))
    cfg = yaml.safe_load((ROOT / 'configs/smoke.yaml').read_text(encoding='utf-8'))
    cfg['model']['use_edge_features'] = True
    cfg['loss']['use_crf_stage'] = True
    cfg['train'].update(num_workers=0, epochs=2, checkpoint=str(OUT / 'checkpoints/combined.pt'),
                        history_path=str(OUT / 'train_history.json'))
    config_path = OUT / 'config.yaml'
    config_path.write_text(yaml.safe_dump(cfg), encoding='utf-8')
    for name, args in [('train', ['scripts/phase3_train_measure.py', '--config', str(config_path),
            '--device', 'cuda', '--measurement', str(OUT / 'train_memory.json')]),
            ('eval', ['scripts/eval.py', '--config', str(config_path), '--checkpoint',
             cfg['train']['checkpoint'], '--output', str(OUT / 'eval_test.json')])]:
        with (OUT / f'{name}.log').open('w', encoding='utf-8') as stream:
            subprocess.run([sys.executable, *args], stdout=stream, stderr=subprocess.STDOUT, check=True)
        print('PASS combined smoke', name, flush=True)
    history = json.loads((OUT / 'train_history.json').read_text())
    assert len(history) == 2
    assert all(math.isfinite(value) for epoch in history for split in ('train', 'val')
               for value in epoch[split].values() if isinstance(value, (int, float)))
    memory = json.loads((OUT / 'train_memory.json').read_text())
    assert memory['below_device_vram'] is True
    evaluation = json.loads((OUT / 'eval_test.json').read_text())
    stages = [s for row in evaluation['per_sample'] for s in row['decoded_stages']]
    from collections import Counter
    result = dict(synthetic_only=True, two_epochs_finite=True, memory=memory,
                  stage_histogram=dict(Counter(stages)), unique_stages=len(set(stages)),
                  unknown_fraction=stages.count(6)/len(stages),
                  illegal_transition_rate=evaluation['metrics']['illegal_transition_rate'],
                  note='Uses configs/smoke.yaml with isolated outputs and zero workers to limit host RAM; frozen tensors unchanged.')
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
