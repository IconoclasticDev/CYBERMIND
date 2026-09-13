"""Independent audit of preservation, original-fixture identity and per-step counts."""
import importlib.util
import json
from pathlib import Path
import sys
import torch

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
spec=importlib.util.spec_from_file_location('helper',ROOT/'examples/phase2_stage_decoder/run_verification.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)


def main():
    result={'baseline':h.verify_baseline(),'prototype_fixture_used':False}
    for group in ('phase3_joint','phase3_balanced_stage'):
        d=ROOT/'examples'/group;m=json.loads((d/'manifest.json').read_text(encoding='utf-8-sig'))
        for name,expected in m['files'].items():assert h.fingerprint(d/name)==expected,name
        for name,expected in m['local_untracked_tensors_and_checkpoints'].items():assert h.fingerprint(d/name)==expected,name
        result[group]={'evidence_files_unchanged':len(m['files']),'local_tensors_unchanged':len(m['local_untracked_tensors_and_checkpoints'])}
    for filename in ('eval_test.json','train_history.json'):
        h.compare_legacy(json.loads((OUT/'original_pipeline'/filename).read_text()),
                         json.loads((ROOT/'examples/phase3_joint/combined'/filename).read_text()))
    result['cpu_rerun_matches_original_combined_within_1e_6']=True
    comparisons={}
    for split in ('train','val','test'):
        a=torch.load(ROOT/f'examples/phase3_joint/combined/processed/{split}.pt',weights_only=False)
        b=torch.load(OUT/f'original_pipeline/processed/{split}.pt',weights_only=False)
        assert len(a)==len(b)
        count=0
        for x,y in zip(a,b):
            assert x.scenario_id==y.scenario_id and len(x.states)==len(y.states)
            for u,v in zip(x.states,y.states):
                assert torch.equal(u.x,v.x) and torch.equal(u.edge_index,v.edge_index) and torch.equal(u.edge_attr,v.edge_attr)
                assert (u.timestamp,u.y_stage,u.y_infiltration,u.metadata.get('campaign_reset'))==(v.timestamp,v.y_stage,v.y_infiltration,v.metadata.get('campaign_reset'))
                count+=1
        comparisons[split]={'sequences':len(a),'state_occurrences_equal':count}
    result['original_fixture_tensor_and_label_comparison']=comparisons
    for p in OUT.glob('*/rollout*.json'):
        report=json.loads(p.read_text())
        for t in range(1,5):
            stages=[row['steps'][t]['decoded_stage'] for row in report['samples']]
            prior=[row['steps'][t-1]['decoded_stage'] for row in report['samples']]
            assert all(0<=s<=6 for s in stages+prior)
            illegal=sum(b<a and a!=6 and b!=6 for a,b in zip(prior,stages))
            summary=report['per_step'][t-1]
            assert summary['illegal_count']==illegal and summary['distinct_non_unknown']==len(set(stages)-{6})
            assert summary['unknown_count']==stages.count(6)
            assert summary['passed']==(illegal==0 and len(set(stages)-{6})>=2 and stages.count(6)<len(stages))
    result['per_step_counts_independently_verified']=True
    (OUT/'preservation_and_reproduction.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    summary={}
    for name in ('original_cuda','crf_weight_zero','crf_per_token','original_frozen_cuda'):
        rows=[json.loads(s) for s in (OUT/name/'training_diagnostics.jsonl').read_text().splitlines()]
        selected=json.loads((OUT/name/'rollout.json').read_text())
        last=json.loads((OUT/name/'rollout_last.json').read_text())
        summary[name]={'first_batch':{k:v for k,v in rows[0].items() if k not in ('emission_logits_before_crf','emission_argmax','labels','transitions_before_optimizer_update')},
            'last_batch':{k:v for k,v in rows[-1].items() if k not in ('emission_logits_before_crf','emission_argmax','labels','transitions_before_optimizer_update')},
            'training_batches':len(rows),'selected_epoch':selected['selected_epoch'],'selected_steps':selected['per_step'],'last_steps':last['per_step']}
    (OUT/'numerical_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
