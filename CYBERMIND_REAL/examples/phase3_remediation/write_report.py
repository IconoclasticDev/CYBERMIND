"""Render the re-audit from completed evidence; failed gates remain failures."""
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


def read(path):
    return json.loads((OUT/path).read_text(encoding='utf-8-sig'))


def main():
    regression = read('regression/verification_status.json')
    assert regression['status'] == 'checks_completed_pending_audit'
    matrix = read('regression/execution_matrix.json')
    preservation = read('preservation.json')
    names = ['exposure100', 'frozen_exposure100', 'normalization_off100', 'class_weighted100',
             'lr_0001_cpu', 'lr_001_cpu', 'lr_003_cpu', 'lr_01_cpu']
    cases = [(name, read(f'{name}/status.json')) for name in names]
    assert all(s['execution'] == 'complete' and s['epochs_completed'] == 100 for _, s in cases)
    assert all(not s['selected_all_steps_pass'] and not s['last_all_steps_pass'] for _, s in cases)
    lines = ['# Phase 3 remediation re-audit', '',
        'Date: 2026-09-13. **Phase 3 exit criteria NOT met.**', '',
        'All five ranked diagnostics in `CYBERMIND_Phase3_Failure_Remediation.pdf` were executed. '
        'Eight 100-epoch experiments completed with finite recorded losses, but every selected checkpoint and every final checkpoint '
        'still predicts one non-Unknown stage across all evaluation samples at each future step 1–4. '
        'No successful collapse fix has been established. Phase 4 remains closed.', '',
        'The source documents are the supplied remediation PDF and `CYBERMIND_Final_Implementation_Plan.pdf`. '
        'The user’s explicit original-fixture, unchanged-gate and four-step requirements govern this audit. '
        'The remediation PDF presents diagnostics, not guaranteed fixes. No prototype fixture, new label signal, '
        'oracle future reset mask, relaxed transition policy, or aggregate-over-time pass was used.', '',
        '## 1. Work completed and numerical diagnosis', '',
        '| Authorized diagnostic | Execution and finding |',
        '| --- | --- |',
        '| More exposure | Original integration: 100 epochs / 400 optimizer updates, versus 2 / 8 originally. Original frozen smoke: 100 / 1,800, versus 2 / 36. Selected and last checkpoints fail all four steps on both fixtures. |',
        '| Normalization ablation | Same canonical rows, labels and topology; identity transform removes centering/scaling. Reapplying original train-fitted normalization reproduces original tensors with maximum error **0** on every split. After 100 epochs both checkpoints still collapse. |',
        '| Label recoverability | Audited both original generators and actual model inputs. Integration has a recoverable periodic clock signal; the frozen fixture has no intended class-conditioned feature signal. Neither finding is a learned-model pass. Details below. |',
        '| Class weighting | Added optional training-only inverse-frequency StageHead cross-entropy weighting. Counts 184 Benign / 60 Recon give weights 0.6630434783 / 2.0333333333; absent classes retain weight 1. CRF NLL and its coefficient remain unchanged. Both checkpoints fail after 100 epochs. |',
        '| CPU learning-rate sweep | Predeclared rates 0.0001, 0.001, 0.003, 0.01; 100 epochs each with the original normalized integration data. All selected and final checkpoints fail all steps. |', '',
        'The production-code change is confined to optional class-balanced CE in `scripts/train.py`; '
        '`loss.stage_class_balance` defaults to false. Weights are calculated from training target occurrences only, '
        'persisted in checkpoint config and reused for validation. No model decoder or checkpoint-selection policy was changed. '
        '`tests/test_stage_class_weights.py` checks invalid inputs, exact default-off loss/gradient/RNG compatibility, '
        'balanced gradient mass, and joint CE-only effects with finite StageHead gradients on CPU and CUDA.', '',
        'The previous [original root-cause audit](PHASE3_ROOT_CAUSE_AUDIT.md) identified pre-CRF emission collapse as the primary observed failure. '
        'Original normalized emission entropy was 0.983, 0.975, 0.961, 0.941 at steps 1–4. Learned transition scores were only about ±0.004; '
        'zeroing learned scores retained collapse. Weighted CRF StageHead gradient magnitude was approximately 2.00–2.04 times CE '
        '(cosine similarity approximately 0.996), but zero-CRF and token-normalized controls also collapsed. '
        'Thus neither a blanket stay-transition preference nor CE/CRF scale alone explained the failure.', '',
        'After 100 integration epochs, maximum across-sample raw-logit standard deviation is '
        '0.000561, 0.000427, 0.000266, 0.000420 and normalized entropy is '
        '0.335430, 0.339622, 0.360058, 0.417165. The emissions became more confident while remaining nearly identical across samples. '
        'Insufficient exposure is therefore not a demonstrated remedy. The high-rate run reaches approximately 0.000016 '
        'maximum logit SD at every step. These are measured downstream symptoms; the precise upstream optimization mechanism '
        'is still unresolved, and no architecture-only causal claim is made.', '',
        '## 2. Independent four-step gate results', '',
        'Each cell is **distinct non-Unknown stages / illegal incoming transitions / Unknown predictions**. '
        'Passing requires at least two known stages, zero illegal transitions and fewer Unknown predictions than samples '
        'at **each** step. Step 1 includes the transition from decoded observed state to first forecast; '
        'later steps use consecutive forecast states. All 64 checkpoint-step checks fail diversity.', '',
        '| Experiment | Checkpoint epoch | Samples per step | Step 1 D/I/U | Step 2 D/I/U | Step 3 D/I/U | Step 4 D/I/U | Verdict |',
        '| --- | ---: | ---: | --- | --- | --- | --- | --- |']
    for name, status in cases:
        for label, key, epoch in [('selected', 'selected_steps', status['selected_epoch']), ('last', 'last_steps', 100)]:
            steps = status[key]
            cells = [f"{s['distinct_non_unknown']}/{s['illegal_count']}/{s['unknown_count']}" for s in steps]
            lines.append(f"| {name} ({label}) | {epoch} | {steps[0]['samples']} | " + ' | '.join(cells) + ' | FAIL |')
    lines += ['', 'Selected checkpoint stages are Recon (1) for normalization-off and class-weighted runs, '
              'C&C (4) for LR 0.0001, and Benign (0) for the other runs. Every epoch-100 checkpoint predicts Benign '
              'at every step for every sample. Zero illegal transitions and zero Unknown predictions do not compensate for collapse.', '',
              'Maximum across-sample **pre-CRF mean-emission logit SD**, final epoch:', '',
              '| Experiment | Step 1 | Step 2 | Step 3 | Step 4 |', '| --- | ---: | ---: | ---: | ---: |']
    for name, status in cases:
        lines.append(f'| {name} | ' + ' | '.join(f"{s['max_across_sample_logit_std']:.8f}" for s in status['last_steps']) + ' |')
    lines += ['', 'Every experiment folder retains `rollout.json` and `rollout_last.json`: full per-sample/per-step '
        'raw StageHead emissions, emission argmax, decoded stages, learned/masked transition values and zero-learned-transition controls. '
        'The unchanged `examples/phase3_root_cause/inspect_rollouts.py` uses `eval.rollout_steps: 4`. '
        '`audit_results.py` independently recomputes all counts from individual paths. A runner exit code of zero '
        'means the experiment executed; its `all_steps_pass: false` remains a failed gate.', '',
        '## 3. Original-data recoverability and limits', '',
        '**Integration fixture:** actual stored history is 3 and forecasting observes 2 states; the remediation PDF’s '
        'history-8 description does not apply to this fixture. Only two node coordinates and one edge coordinate vary. '
        'Existing normalized `bytes_total` has slope 0.02793721242224979 per second. A training-only analytical diagnostic '
        'recovers the shortest exact label period of 4 seconds. Maximum reconstructed clock error is 1.96e-6 seconds '
        'on train, 4.30e-6 on validation and 4.16e-6 on test. All available actual future labels are reconstructed at steps 1–4 '
        '(test denominators 25, 24, 23, 22; boundary futures excluded). This establishes retained information, '
        'not that the neural encoder learns or generalizes that rule. No diagnostic output enters model features or decoding.', '',
        'All 27 validation and all 27 test window coordinates lie beyond the training coordinate range. '
        'Generalization requires periodic extrapolation from a continuous trend. Original normalization was fitted '
        'on training only, not globally; neither floating-point erasure nor leakage from global normalization explains this result.', '',
        '**Frozen smoke fixture:** stored history is 8, with 7 observed states. Training stage targets are '
        '102 Benign / 12 Initial Access / 12 Exfiltration; validation and test each contain 17 / 2 / 2. '
        'Attack status is generated from hidden sample index `i % 3`, while model-visible node/edge features are random '
        'draws conditional on node count. Every training node count includes both benign and attack sequences, and all '
        'evaluation node counts occur in training. The generator supplies no intended class-conditioned feature distribution. '
        'This is not a proof that finite tensors cannot be memorized or show accidental correlation. Only rollout step 1 '
        'has stored ground truth; steps 2–4 permit diversity/legality checks but no accuracy claim.', '',
        '**Gate/contract questions remain for review:** the original main PDF’s nonzero illegal-transition wording '
        'conflicts with the Phase 2 hard mask and the user’s later zero-illegal requirement. This audit applies the explicit '
        'user requirement and does not introduce illegal transitions. The integration labels also contain declared Recon-to-Benign '
        'resets during training, whereas the original forecast gate has no future reset declarations. No oracle reset metadata '
        'was added at evaluation. These issues are flagged; no gate was revised and no replacement experiment is proposed as a pass.', '',
        '## 4. Real checkpoint selection', '',
        '**PASS — validation-metric-based in the active training path.** `validate()` runs on `val_loader`; '
        '`metrics[\'f1\']` is infiltration F1 at threshold 0.5, not stage F1 or training loss. '
        'Selected epochs across the diagnostics are 1, 1, 2, 1, 1, 71, 28, 1 in table order. '
        'The epoch-100 checkpoint is audited separately and never substituted for the selected checkpoint.', '']
    source = (ROOT/'scripts/train.py').read_text(encoding='utf-8').splitlines()
    start = next(i for i, s in enumerate(source) if 'metrics = validate(model, val_loader' in s)
    end = next(i for i in range(start, len(source)) if "torch.save(payload, checkpoint.with_name" in source[i])
    lines += [f'Exact active `scripts/train.py`, lines **{start+1}–{end+1}**:', '', '```python', *source[start:end+1], '```', '',
        'The historical outer `multisource_audit/CYBERMIND_REAL/scripts/train.py` selects training loss, '
        'as documented in the previous root-cause report. That archived path is not invoked here. '
        'Validation infiltration F1 selection is verified, but it does not guarantee stage diversity; final checkpoints also fail.', '',
        '## 5. Main-plan regression and preservation re-audit', '',
        '| Feature flags | Full suite, CPU and actual CUDA cases | Two-epoch CPU integration |',
        '| --- | --- | --- |']
    for row in matrix:
        lines.append(f"| {row['name']} | {row['tests_passed']} passed, {row['skipped']} skipped | Executed; finite losses and explanations |")
    lines += ['', f"Total: **{sum(r['tests_passed'] for r in matrix)} test executions** across four flag contexts. "
        'The new weighted-CE integration case passed on CPU and CUDA. Fresh both-off history/evaluation and '
        'frozen checkpoint evaluation match Phase 0 within 1e-6. The combined two-epoch CUDA pipeline also completed. '
        'These are software/regression passes, not a model diversity pass.', '',
        'The 100-epoch CUDA run reserved 92,274,688 bytes (88 MiB), below runtime-confirmed '
        '8,518,041,600 bytes. This is the training process’s PyTorch allocator measurement, excluding driver and other processes. '
        'All 800 diagnostic epochs have finite recorded train/validation numbers. Negative Gaussian NLL totals '
        'are not treated as evidence of stage learning.', '',
        'All **49** Phase 0 files remain unchanged. Preserved evidence also matches every recorded hash: '
        'Phase 3 joint **112 files + 27 local tensors/checkpoints**, rejected balanced fixture **14 + 5**, '
        'original root-cause audit **63 + 13**. Preservation of rejected evidence is not reuse as a gate. '
        '`configs/gb10_edge_only.yaml`, `configs/gb10_crf_only.yaml` and `configs/gb10_baseline.yaml` '
        'are unchanged relative to pre-remediation commit `38d0449`. No Phase 4 work or dataset download occurred.', '',
        'Evidence is in [examples/phase3_remediation](examples/phase3_remediation/), including predeclared '
        '`remaining_plan.json`, per-run configs/history/memory/status/logs, recoverability audits, '
        '`preservation.json`, regression JUnit XML and `manifest.json`. Checkpoints and processed tensors remain local '
        'and are hash-recorded separately. Original inputs and historical reports are retained.', '',
        '## 6. Final verdict and remaining work', '',
        '**Phase 3 exit criteria NOT met.**', '',
        'The authorized diagnostic plan is complete, but it did not fix the original failure. '
        'What remains is a demonstrated model fix on the original non-prototype data: at least two non-Unknown '
        'stages and zero illegal transitions independently at each of four rollout steps, with finite training, '
        'unchanged regression behavior and valid checkpoint selection. The upstream learning failure still needs '
        'a proven remedy; successful analytical label reconstruction and additional confidence are insufficient.', '',
        'The fixture/transition-contract questions above require review before any gate revision. '
        'No replacement gate has been installed. Phase 4 must not begin on this failed result.', '']
    (ROOT/'PHASE3_REMEDIATION_REAUDIT.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
