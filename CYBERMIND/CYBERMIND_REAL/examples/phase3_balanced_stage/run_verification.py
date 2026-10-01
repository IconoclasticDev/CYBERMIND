"""Approved Phase 3 diversity check; deliberately learnable synthetic regimes only.

No production feature semantics, real corpus, or detection-quality claim. Fixture
design and seeds are fixed before training; test results never select parameters.
"""
from collections import Counter
import datetime
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')


def fingerprint(path):
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def verify_preserved():
    base = ROOT / 'examples/smoke/baseline_before'
    manifest = json.loads((base / 'baseline_manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files'].items():
        assert fingerprint(base / name) == expected, name
    assert fingerprint(base / 'baseline_manifest.json')['sha256'] == '46be0cc83ad87bf462b9c661e6b55935b90427d3e80311287ffff91c7572e90b'
    old = ROOT / 'examples/phase3_joint'
    prior = json.loads((old / 'manifest.json').read_text(encoding='utf-8-sig'))
    for name, expected in prior['files'].items():
        assert fingerprint(old / name) == expected, name
    for name, expected in prior['local_untracked_tensors_and_checkpoints'].items():
        assert fingerprint(old / name) == expected, name
    return dict(frozen_baseline_files=len(manifest['files']), original_phase3_evidence_files=len(prior['files']),
                original_phase3_local_tensors=len(prior['local_untracked_tensors_and_checkpoints']))


def generate():
    import torch
    from cybermind.data.types import GraphState, GraphSequenceSample
    processed = OUT / 'processed'
    processed.mkdir(exist_ok=True)
    # Equal stage coverage. Node/edge prototype coordinates directly represent
    # a synthetic observable regime, deliberately unlike real network features.
    edges = torch.tensor([[0,2,1,2,0,1], [1,1,0,0,2,2]], dtype=torch.long)
    splits = [('train', 314159, 32), ('val', 271828, 8), ('test', 161803, 8)]
    keys, tensor_hashes, report = {}, {}, {}
    for split_index, (split, seed, per_stage) in enumerate(splits):
        rng = torch.Generator().manual_seed(seed)
        samples = []
        for stage in range(6):
            for sample_index in range(per_stage):
                scenario = f'SYNTHETIC_BALANCED::{split}::{stage}::{sample_index}'
                campaign_start = 1800000000. + split_index * 1000000 + (stage * per_stage + sample_index) * 1000
                states = []
                # A persistent 8-window regime segment; later-stage segments
                # start inside their own campaign rather than declaring resets.
                segment_start = campaign_start + stage * 8
                prototype = torch.zeros(14)
                prototype[stage] = 3.
                for step in range(8):
                    x = prototype.expand(3, -1).clone() + .05 * torch.randn(3,14,generator=rng)
                    x[:, 6:9] += torch.eye(3)
                    edge_attr = .05 * torch.randn(6,7,generator=rng)
                    edge_attr[:, stage] += torch.linspace(.5,1.5,6)
                    edge_attr[:, 6] += torch.linspace(0.,1.,6)
                    timestamp = segment_start + step
                    metadata = dict(source='PHASE3_BALANCED_SYNTHETIC', split=split,
                                    campaign_start=campaign_start, window_start=timestamp,
                                    campaign_reset=bool(step == 0 and stage in (0,1)),
                                    campaign_reset_source='independent fixture campaign boundary',
                                    synthetic_only=True)
                    states.append(GraphState(x=x, edge_index=edges.clone(), edge_attr=edge_attr,
                        node_ids=['a','b','c'], timestamp=timestamp, y_infiltration=float(stage >= 2),
                        y_stage=stage, scenario_id=scenario, attack_label='SYNTHETIC_REGIME', metadata=metadata))
                samples.append(GraphSequenceSample(states,scenario,segment_start,1.,{'synthetic_only':True}))
        keys[split] = {(s.scenario_id,s.timestamp) for sample in samples for s in sample.states}
        tensor_hashes[split] = {hashlib.sha256(s.x.numpy().tobytes()+s.edge_attr.numpy().tobytes()).hexdigest()
                                for sample in samples for s in sample.states}
        counts = Counter(s.y_stage for sample in samples for s in sample.states[1:])
        assert set(counts) == set(range(6)) and len(set(counts.values())) == 1
        assert all(torch.isfinite(s.x).all() and torch.isfinite(s.edge_attr).all()
                   for sample in samples for s in sample.states)
        torch.save(samples, processed / f'{split}.pt')
        report[split] = dict(seed=seed, samples=len(samples), target_stage_counts=dict(counts),
                             tensor_file=fingerprint(processed/f'{split}.pt'))
    for a,b in [('train','val'),('train','test'),('val','test')]:
        assert keys[a].isdisjoint(keys[b]) and tensor_hashes[a].isdisjoint(tensor_hashes[b])
    write('fixture_manifest.json', dict(synthetic_only=True, splits=report, split_windows_disjoint=True,
        feature_tensors_disjoint=True, node_width=14, edge_width=7, history=8,
        description='Six equally represented persistent regimes with direct artificial feature prototypes and independent Gaussian jitter; not real network telemetry.',
        boundary_rule='Independent campaigns; reset declaration only at first position of stage 0/1 segments. No inferred label/prediction-dependent resets.',
        gate_fixed_before_training={'illegal_transition_rate':0.,'minimum_distinct_non_unknown_future_stages':2},
        no_test_based_tuning=True))


def main():
    # Reject reruns before any recorded status or experiment file can change.
    if (OUT/'train_history.json').exists():
        raise FileExistsError('Use a fresh evidence directory for a new experiment.')
    os.chdir(ROOT)
    os.environ.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONHASHSEED='42', PYTHONUTF8='1')
    temp = ROOT / '.phase3-tmp'
    temp.mkdir(exist_ok=True)
    os.environ.update(TEMP=str(temp),TMP=str(temp))
    import torch
    import yaml
    assert torch.cuda.is_available(), 'Actual CUDA is required for this gate.'
    torch.set_num_threads(2)
    status = dict(phase=3, status='running', approved_revision=True, synthetic_only=True, commands=[],
                  started_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    def run(name, args, cpu=False):
        env = os.environ.copy()
        if cpu:
            env['CUDA_VISIBLE_DEVICES'] = ''
        command = [sys.executable, *args]
        start = time.monotonic()
        print('START',name,flush=True)
        with (OUT/f'{name}.log').open('w',encoding='utf-8') as log:
            result = subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        status['commands'].append(dict(name=name,command=command,cpu_only=cpu,exit_code=result.returncode,
                                       seconds=round(time.monotonic()-start,3)))
        write('verification_status.json',status)
        assert result.returncode == 0, f'See {name}.log'
        print('PASS',name,flush=True)
    try:
        status['preserved_before'] = verify_preserved()
        generate()
        cfg = yaml.safe_load((ROOT/'configs/smoke.yaml').read_text(encoding='utf-8'))
        cfg['data'].update(processed_dir=str(OUT/'processed'), history=8, window_seconds=1, stride_seconds=1)
        cfg['model']['use_edge_features'] = True
        cfg['loss']['use_crf_stage'] = True
        cfg['train'].update(epochs=2,num_workers=0,checkpoint=str(OUT/'checkpoints/combined.pt'),
                            history_path=str(OUT/'train_history.json'))
        (OUT/'config.yaml').write_text(yaml.safe_dump(cfg),encoding='utf-8')
        run('train_cuda',['scripts/phase3_train_measure.py','--config',str(OUT/'config.yaml'),
            '--device','cuda','--measurement',str(OUT/'train_memory.json')])
        history = json.loads((OUT/'train_history.json').read_text())
        assert len(history)==2 and all(math.isfinite(v) for e in history for split in ('train','val')
                                     for v in e[split].values() if isinstance(v,(int,float)))
        memory = json.loads((OUT/'train_memory.json').read_text())
        assert memory['status']=='passed' and memory['below_device_vram'] is True
        status.update(two_epochs_finite=True,memory=memory)
        for device in ('cuda','cpu'):
            run(f'eval_{device}',['scripts/eval.py','--config',str(OUT/'config.yaml'),
                '--checkpoint',cfg['train']['checkpoint'],'--output',str(OUT/f'eval_{device}.json')],cpu=device=='cpu')
            report = json.loads((OUT/f'eval_{device}.json').read_text())
            # Gate only actual future positions, not the observed step-zero state.
            future = [stage for row in report['per_sample'] for stage in row['decoded_stages'][1:]]
            all_stages = [stage for row in report['per_sample'] for stage in row['decoded_stages']]
            result = dict(future_histogram=dict(Counter(future)),all_positions_histogram=dict(Counter(all_stages)),
                          distinct_non_unknown_future_stages=len(set(future)-{6}),unknown_fraction=future.count(6)/len(future),
                          illegal_transition_rate=report['metrics']['illegal_transition_rate'],
                          evaluated_pairs=report['metrics']['stage_transition_pairs'])
            status[device]=result
            write('verification_status.json',status)
            assert result['evaluated_pairs']>0 and result['illegal_transition_rate']==0
            assert result['distinct_non_unknown_future_stages']>=2, f'{device} diversity gate failed: {result}'
        status['preserved_after']=verify_preserved()
        assert status['preserved_before']==status['preserved_after']
        status['status']='passed'
    except Exception as exc:
        status.update(status='failed',error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        status['finished_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        write('verification_status.json',status)
    print('APPROVED PHASE 3 DIVERSITY GATE PASSED',flush=True)


if __name__=='__main__':
    main()
