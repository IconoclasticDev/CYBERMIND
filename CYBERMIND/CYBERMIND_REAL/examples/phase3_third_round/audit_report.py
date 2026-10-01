"""Final requirement audit for reviewed Phase 3, with no test-based selection."""
from pathlib import Path
import importlib.util
import json
import math
import subprocess
import sys
import torch

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from cybermind.utils.checkpoint_selection import CheckpointSelection
GIT=r'C:\Users\as030\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))


def exact_state(a,b):
    if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and torch.equal(a,b)
    if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(exact_state(v,b[k]) for k,v in a.items())
    if isinstance(a,(list,tuple)):return type(a)==type(b) and len(a)==len(b) and all(exact_state(x,y) for x,y in zip(a,b))
    return a==b


def main():
    folder=OUT/'extended200';history=read(folder/'train_history.json')
    checkpoint=torch.load(folder/'checkpoints/combined.pt',map_location='cpu',weights_only=False)
    assert checkpoint['epoch']==185
    selector=CheckpointSelection(checkpoint['config']['train']);events=[]
    for row in history:
        changed=selector.update(row['epoch'],row['val'])
        events.append(dict(epoch=row['epoch'],selected_now=changed,state=selector.state_dict()))
    assert selector.selected_epoch==checkpoint['epoch'] and selector.tolerance==.05
    assert checkpoint['validation']==history[184]['val']
    assert checkpoint['selection_state']==selector.state_dict()
    assert len(history)==200 and all(math.isfinite(v) for r in history for split in ('train','val') for v in r[split].values() if isinstance(v,(int,float)))
    evidence={'selection_recomputed_from_all_200_validation_epochs':True,'selected_epoch':185,'selection_events':events}
    reports={name:read(folder/file) for name,file in [('retrospective98','rollout98.json'),('selected185','rollout.json'),('last200','rollout_last.json')]}
    for report in reports.values():
        assert len(report['per_step'])==4
        for t,s in enumerate(report['per_step'],1):
            stages=[r['steps'][t]['decoded_stage'] for r in report['samples']]
            prior=[r['steps'][t-1]['decoded_stage'] for r in report['samples']]
            distinct=len(set(stages)-{6});unknown=stages.count(6)
            illegal=sum(b<a and a!=6 and b!=6 for a,b in zip(prior,stages))
            assert (distinct,illegal,unknown)==(s['distinct_non_unknown'],s['illegal_count'],s['unknown_count'])
            assert s['passed']==(distinct>=2 and illegal==0 and unknown<len(stages))
        assert report['all_steps_pass']==all(s['passed'] for s in report['per_step'])
    assert reports['selected185']['all_steps_pass']
    evidence['selected_checkpoint_all_four_steps_independently_verified']=True
    old=torch.load(ROOT/'examples/phase3_second_escalation/periodic100/checkpoints/combined_last.pt',map_location='cpu',weights_only=False)
    replay=torch.load(folder/'reproduced100/combined_last.pt',map_location='cpu',weights_only=False)
    assert old['model_state'].keys()==replay['model_state'].keys()
    assert all(torch.equal(v,replay['model_state'][k]) for k,v in old['model_state'].items())
    assert exact_state(old['optimizer_state'],replay['optimizer_state'])
    evidence['replayed_epoch100_model_bitwise_matches_original']=True
    evidence['replayed_epoch100_optimizer_state_exactly_matches_original']=True
    del old,replay,checkpoint
    spec=importlib.util.spec_from_file_location('old_helpers',ROOT/'examples/phase2_stage_decoder/run_verification.py')
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    evidence['baseline']=h.verify_baseline()
    h.compare_legacy(history[:100],read(ROOT/'examples/phase3_second_escalation/periodic100/train_history.json'))
    for name in ('phase3_joint','phase3_balanced_stage','phase3_root_cause','phase3_remediation','phase3_second_escalation'):
        directory=ROOT/'examples'/name;manifest=read(directory/'manifest.json');counts={}
        for category in ('files','local_untracked_tensors_and_checkpoints'):
            for filename,expected in manifest[category].items():assert h.fingerprint(directory/filename)==expected,(name,filename)
            counts[category]=len(manifest[category])
        evidence[name]=counts
    assert not subprocess.check_output([GIT,'diff','2d5b6a8','--','configs/gb10_*.yaml','scripts/make_synthetic.py'],cwd=ROOT)
    evidence['protected_configs_and_generator_unchanged']=True
    regression=read(OUT/'regression/verification_status.json');assert regression['status']=='checks_completed_pending_audit'
    matrix=read(OUT/'regression/execution_matrix.json')
    evidence['phase2_exit_checks']={r['name']:h.verify_matrix(OUT/f"regression/pytest_{r['name']}.xml") for r in matrix}
    resume=read(OUT/'resume_validation/verification.json')
    assert resume['all_history_fields_match_within_1e_6'] and all(r['all_model_tensors_bitwise_equal'] for r in resume['checkpoints'].values())
    spec=importlib.util.spec_from_file_location('frozen',ROOT/'examples/phase3_second_escalation/frozen_gate.py')
    frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
    original_frozen=ROOT/'examples/phase3_root_cause/original_frozen_cuda'
    diagnostics=json.loads((original_frozen/'training_diagnostics.jsonl').read_text().splitlines()[0])
    norms=diagnostics['gradients']['stage_head_weight']
    for suffix in ('','_last'):
        assert frozen.judge_frozen(read(original_frozen/f'rollout{suffix}.json')['per_step'],read(original_frozen/'train_history.json'),[norms['ce_norm'],norms['crf_norm']])
    evidence['reviewed_frozen_gate_reverified']=True
    (OUT/'preservation_and_completion.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    lines=['# Phase 3 final audit — reviewed selection and extension','',
        '**Phase 3 exit criteria met.** Date: 2026-09-13. This verdict applies to the explicitly reviewed Phase 3 scope: '
        'unchanged four-step integration diversity/legality gate, approved periodic input representation, approved frozen-fixture '
        'mechanical gate and approved validation-only checkpoint policy. Phase 4 has not started and requires separate approval.','',
        'The actual training loop selected **epoch 185**. Its validation infiltration F1 is **1.0**, validation stage '
        'cross-entropy **0.0095255390**, and it passes the integration gate at **all four forecast steps**. '
        'The tolerance remained exactly **0.05** throughout. No test result or final-epoch preference entered selection.','',
        '## Authorization and work completed','',
        'The user approved Option 2 in `CYBERMIND_Reviewer_Decision_Tolerance.pdf` and the accompanying message: '
        'absolute F1 tolerance 0.05, validation stage CE as the lower-is-better tie-breaker, exact sequential pseudocode, '
        'and extension beyond epoch 100 if needed. The earlier frozen Option 2 and periodic input decisions remain in effect. '
        '[REVIEW_DECISION.md](examples/phase3_third_round/REVIEW_DECISION.md) records the precise scope and the '
        '**epoch-200 extension budget fixed before training**, with no subsequent tolerance adjustment.','',
        'Implemented `CheckpointSelection` in the real `scripts/train.py` path. The opt-in configuration is '
        '`selection_metric: val_f1_stage_band`, `selection_f1_tolerance: 0.05`, `selection_stage_metric: stage`. '
        '`stage` maps to the existing validation StageHead CE, not CRF NLL, train loss or test diversity. '
        'Existing configurations retain the original `val_f1` default. Protected GB10 configs were not edited; '
        'enabling the approved policy in future GB10 configs belongs to the separately approved configuration phase.','',
        'Checkpoint payloads now preserve selection state and Python/NumPy/PyTorch RNG state. Resume reconstructs '
        'selection from validation history, checks policy/tolerance/metric compatibility, restores RNG, and retains '
        'the previously selected model even when the continuation uses another output directory. '
        'The selector is independent of edge, CRF and class-balance flags; opting out retains original selection behavior.','',
        '## Actual retrospective result and replay','',
        'The document correctly excludes epoch 100 but incorrectly predicts epoch 94 remains selected. '
        'Applying its exact pseudocode to **all 100 recorded validation epochs selects epoch 98**, with F1 **1.0** '
        'and stage CE **0.2919362330**. The complete validation-only selection trace was saved before any new training. '
        'Only epochs 94/100 originally had saved weights, so epoch 98 was recovered by deterministic replay; '
        'it was never replaced with a nearby available checkpoint.','',
        'All 100 replayed train/validation histories match the original within **1e-6**, and every epoch-100 model '
        'tensor matches the original **bit for bit**; optimizer state and parameter groups also match exactly. Recovered epoch 98 fails only step 1 of the integration gate. '
        'The authorized extension resumed epoch-100 model and optimizer state through epoch 200, retaining the '
        'same data, periodic transform, architecture, losses, LR, seed and four-step evaluation protocol. '
        'Patience 201 permits the declared budget. Every recorded train/validation loss is finite.','',
        'The supplied monotonicity claim is also qualified: validation stage CE rises from 0.291936 at epoch 98 '
        'to 0.304556 at epoch 99 before falling to 0.277114 at epoch 100. The extension was an authorized '
        'experiment, not a guaranteed result inferred from monotonicity. The 0.05 tolerance is a reviewer-set '
        'policy, not a statistically established confidence bound on overlapping synthetic sequences.','',
        '## Per-step integration gate','',
        'Each row covers 25 original test samples, four rollout trajectories, unchanged seed/protocol and no oracle '
        'future resets. Passing requires at least two non-Unknown stages, zero illegal incoming transitions, and '
        'fewer Unknowns than samples at every future step independently. Stage IDs 0/1 are Benign/Recon.','',
        '| Checkpoint | Step | Distinct known | Illegal transitions | Unknown count | Histogram | Verdict |',
        '| --- | ---: | ---: | ---: | ---: | --- | --- |']
    for name,report in reports.items():
        for s in report['per_step']:
            lines.append(f"| {name} | {s['step']} | {s['distinct_non_unknown']} | {s['illegal_count']} | {s['unknown_count']} | {s['decoded_histogram']} | {'PASS' if s['passed'] else 'FAIL'} |")
    lines+=['','The selected epoch 185 passes every step. The epoch-200 last checkpoint fails step 1 and has '
        'validation F1 **0.1538461538**, stage CE **0.3690144968**. It is preserved as a failed result and is not shipped '
        'in place of the validation-selected model. Independently replaying the approved selector over all 200 '
        'validation records reproduces epoch 185; checkpoint metadata and saved state match that decision.','',
        '## Exact real-path selection logic','',
        '**PASS — validation-metric-based.** The following implementation is the reviewer’s sequential rule; '
        '`metrics` comes from validation, and no test-set metric is passed to it. The algorithmic `best_f1` anchor '
        'updates only in the branches specified by the reviewer; it is not silently replaced with an unconditional '
        'maximum or a retrospective global-band ranking.','']
    source=(ROOT/'src/cybermind/utils/checkpoint_selection.py').read_text().splitlines()
    start=next(i for i,s in enumerate(source) if 'stage_ce = metrics' in s)
    end=next(i for i in range(start,len(source)) if source[i]=='        return False')
    lines += [f'`src/cybermind/utils/checkpoint_selection.py`, lines {start+1}–{end+1}:','','```python',*source[start:end+1],'```','']
    source=(ROOT/'scripts/train.py').read_text().splitlines()
    start=next(i for i,s in enumerate(source) if 'metrics = validate(model, val_loader' in s)
    end=next(i for i in range(start,len(source)) if 'torch.save(payload, checkpoint.with_name' in source[i])
    lines += [f'`scripts/train.py`, lines {start+1}–{end+1}, real validation and save path:','','```python',*source[start:end+1],'```','',
        '## Regression, resume and preservation','',
        '| Flag context | Full suite (CPU + actual CUDA cases) | CPU integration |',
        '| --- | --- | --- |']
    for row in matrix:lines.append(f"| {row['name']} | {row['tests_passed']} passed, {row['skipped']} skipped | Completed, finite losses and explanations |")
    lines += ['',f"**{sum(r['tests_passed'] for r in matrix)} test executions**, zero skips across four flag contexts. "
        'Fourteen focused selection tests cover strict/inclusive band boundaries, outside-band rejection, exact '
        'anchor semantics, invalid metrics/config and legacy min-delta behavior. Fresh both-off history/evaluation '
        'and frozen-checkpoint evaluation retain Phase 0 parity within 1e-6. The combined CUDA pipeline completes '
        'with finite losses below device memory capacity. An initial automatic approval-service usage-limit rejection '
        'prevented launch; after checking the local-only command and the user’s continuation instruction, the retry '
        'was approved and the actual required checks completed.','',
        'A separate four-epoch uninterrupted-versus-two-plus-two resumed run has matching histories within 1e-6, '
        '**bitwise-equal selected and last model tensors**, and identical selection state. This verifies actual '
        'training continuity, not just selector arithmetic.','',
        'The approved frozen mechanical gate was reverified on both original checkpoints: zero illegal transitions '
        'at all four steps, finite positive supervised CE/CRF losses and nonzero StageHead gradients. '
        'The fixture remains unchanged and no frozen diversity requirement was reintroduced.','',
        'All preserved evidence matches recorded hashes: Phase 0 **49 files**; original Phase 3 **112 + 27** '
        'evidence/local tensor files; rejected balanced fixture **14 + 5**; root-cause **63 + 13**; first remediation '
        '**187 + 44**; second escalation **114 + 27**. Historical source hashes describe their original revisions; '
        'the new manifest records intentionally changed active training code. Protected `configs/gb10_*.yaml` '
        'and `scripts/make_synthetic.py` are unchanged.','',
        '## Final completion audit','',
        '| Requirement | Evidence / verdict |','| --- | --- |',
        '| Fixed reviewer tolerance and stage-CE tie-breaker in real training | PASS: config 0.05; literal sequential selector; no test-based ranking |',
        '| Existing validation history re-scored honestly | PASS: epoch 98, complete trace; document’s epoch-94 prediction corrected |',
        '| Exact selected checkpoint independently evaluated | PASS: recovered 98 failure recorded; selected extended epoch 185 passes steps 1–4 |',
        '| Authorized continuation on original data | PASS: first-100 parity, saved-RNG resume, 200 finite epochs, unchanged input hashes |',
        '| Reviewed frozen scope | PASS: mechanical gate retained; no regeneration |',
        '| Four-flag CPU/CUDA and legacy regression | PASS: all suites, actual CUDA pipeline, checkpoint/baseline and resume parity |',
        '| Audit, checklist and provenance | PASS: this report, decision record, raw logs/paths and manifest |',
        '| Phase 4 prohibition | Satisfied: no Phase 4 work; separate approval required |','',
        '**Phase 3 exit criteria met.** The passing checkpoint is '
        '`examples/phase3_third_round/extended200/checkpoints/combined.pt` (**epoch 185**), not `combined_last.pt`. '
        'This is laptop synthetic verification under the recorded reviewer decisions, not evidence of real-corpus '
        'accuracy or GB10 deployment readiness. Full corpus acquisition remains deferred to Phase 5.','']
    (ROOT/'PHASE3_FINAL_AUDIT.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Completion evidence verified; Phase 3 final audit written.')


if __name__=='__main__':main()
