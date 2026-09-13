# Phase 3 remediation re-audit

Date: 2026-09-13. **Phase 3 exit criteria NOT met.**

All five ranked diagnostics in `CYBERMIND_Phase3_Failure_Remediation.pdf` were executed. Eight 100-epoch experiments completed with finite recorded losses, but every selected checkpoint and every final checkpoint still predicts one non-Unknown stage across all evaluation samples at each future step 1–4. No successful collapse fix has been established. Phase 4 remains closed.

The source documents are the supplied remediation PDF and `CYBERMIND_Final_Implementation_Plan.pdf`. The user’s explicit original-fixture, unchanged-gate and four-step requirements govern this audit. The remediation PDF presents diagnostics, not guaranteed fixes. No prototype fixture, new label signal, oracle future reset mask, relaxed transition policy, or aggregate-over-time pass was used.

## 1. Work completed and numerical diagnosis

| Authorized diagnostic | Execution and finding |
| --- | --- |
| More exposure | Original integration: 100 epochs / 400 optimizer updates, versus 2 / 8 originally. Original frozen smoke: 100 / 1,800, versus 2 / 36. Selected and last checkpoints fail all four steps on both fixtures. |
| Normalization ablation | Same canonical rows, labels and topology; identity transform removes centering/scaling. Reapplying original train-fitted normalization reproduces original tensors with maximum error **0** on every split. After 100 epochs both checkpoints still collapse. |
| Label recoverability | Audited both original generators and actual model inputs. Integration has a recoverable periodic clock signal; the frozen fixture has no intended class-conditioned feature signal. Neither finding is a learned-model pass. Details below. |
| Class weighting | Added optional training-only inverse-frequency StageHead cross-entropy weighting. Counts 184 Benign / 60 Recon give weights 0.6630434783 / 2.0333333333; absent classes retain weight 1. CRF NLL and its coefficient remain unchanged. Both checkpoints fail after 100 epochs. |
| CPU learning-rate sweep | Predeclared rates 0.0001, 0.001, 0.003, 0.01; 100 epochs each with the original normalized integration data. All selected and final checkpoints fail all steps. |

The production-code change is confined to optional class-balanced CE in `scripts/train.py`; `loss.stage_class_balance` defaults to false. Weights are calculated from training target occurrences only, persisted in checkpoint config and reused for validation. No model decoder or checkpoint-selection policy was changed. `tests/test_stage_class_weights.py` checks invalid inputs, exact default-off loss/gradient/RNG compatibility, balanced gradient mass, and joint CE-only effects with finite StageHead gradients on CPU and CUDA.

The previous [original root-cause audit](PHASE3_ROOT_CAUSE_AUDIT.md) identified pre-CRF emission collapse as the primary observed failure. Original normalized emission entropy was 0.983, 0.975, 0.961, 0.941 at steps 1–4. Learned transition scores were only about ±0.004; zeroing learned scores retained collapse. Weighted CRF StageHead gradient magnitude was approximately 2.00–2.04 times CE (cosine similarity approximately 0.996), but zero-CRF and token-normalized controls also collapsed. Thus neither a blanket stay-transition preference nor CE/CRF scale alone explained the failure.

After 100 integration epochs, maximum across-sample raw-logit standard deviation is 0.000561, 0.000427, 0.000266, 0.000420 and normalized entropy is 0.335430, 0.339622, 0.360058, 0.417165. The emissions became more confident while remaining nearly identical across samples. Insufficient exposure is therefore not a demonstrated remedy. The high-rate run reaches approximately 0.000016 maximum logit SD at every step. These are measured downstream symptoms; the precise upstream optimization mechanism is still unresolved, and no architecture-only causal claim is made.

## 2. Independent four-step gate results

Each cell is **distinct non-Unknown stages / illegal incoming transitions / Unknown predictions**. Passing requires at least two known stages, zero illegal transitions and fewer Unknown predictions than samples at **each** step. Step 1 includes the transition from decoded observed state to first forecast; later steps use consecutive forecast states. All 64 checkpoint-step checks fail diversity.

| Experiment | Checkpoint epoch | Samples per step | Step 1 D/I/U | Step 2 D/I/U | Step 3 D/I/U | Step 4 D/I/U | Verdict |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| exposure100 (selected) | 1 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| exposure100 (last) | 100 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| frozen_exposure100 (selected) | 1 | 3 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| frozen_exposure100 (last) | 100 | 3 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| normalization_off100 (selected) | 2 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| normalization_off100 (last) | 100 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| class_weighted100 (selected) | 1 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| class_weighted100 (last) | 100 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| lr_0001_cpu (selected) | 1 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| lr_0001_cpu (last) | 100 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| lr_001_cpu (selected) | 71 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| lr_001_cpu (last) | 100 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| lr_003_cpu (selected) | 28 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| lr_003_cpu (last) | 100 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| lr_01_cpu (selected) | 1 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |
| lr_01_cpu (last) | 100 | 25 | 1/0/0 | 1/0/0 | 1/0/0 | 1/0/0 | FAIL |

Selected checkpoint stages are Recon (1) for normalization-off and class-weighted runs, C&C (4) for LR 0.0001, and Benign (0) for the other runs. Every epoch-100 checkpoint predicts Benign at every step for every sample. Zero illegal transitions and zero Unknown predictions do not compensate for collapse.

Maximum across-sample **pre-CRF mean-emission logit SD**, final epoch:

| Experiment | Step 1 | Step 2 | Step 3 | Step 4 |
| --- | ---: | ---: | ---: | ---: |
| exposure100 | 0.00056064 | 0.00042696 | 0.00026592 | 0.00042022 |
| frozen_exposure100 | 0.00026542 | 0.00026704 | 0.00026812 | 0.00026927 |
| normalization_off100 | 0.00028864 | 0.00033265 | 0.00034796 | 0.00033681 |
| class_weighted100 | 0.00090422 | 0.00099490 | 0.00110864 | 0.00121757 |
| lr_0001_cpu | 0.00281582 | 0.00239706 | 0.00229981 | 0.00251109 |
| lr_001_cpu | 0.00120255 | 0.00121506 | 0.00129492 | 0.00147014 |
| lr_003_cpu | 0.00062875 | 0.00064945 | 0.00067311 | 0.00070045 |
| lr_01_cpu | 0.00001569 | 0.00001571 | 0.00001615 | 0.00001610 |

Every experiment folder retains `rollout.json` and `rollout_last.json`: full per-sample/per-step raw StageHead emissions, emission argmax, decoded stages, learned/masked transition values and zero-learned-transition controls. The unchanged `examples/phase3_root_cause/inspect_rollouts.py` uses `eval.rollout_steps: 4`. `audit_results.py` independently recomputes all counts from individual paths. A runner exit code of zero means the experiment executed; its `all_steps_pass: false` remains a failed gate.

## 3. Original-data recoverability and limits

**Integration fixture:** actual stored history is 3 and forecasting observes 2 states; the remediation PDF’s history-8 description does not apply to this fixture. Only two node coordinates and one edge coordinate vary. Existing normalized `bytes_total` has slope 0.02793721242224979 per second. A training-only analytical diagnostic recovers the shortest exact label period of 4 seconds. Maximum reconstructed clock error is 1.96e-6 seconds on train, 4.30e-6 on validation and 4.16e-6 on test. All available actual future labels are reconstructed at steps 1–4 (test denominators 25, 24, 23, 22; boundary futures excluded). This establishes retained information, not that the neural encoder learns or generalizes that rule. No diagnostic output enters model features or decoding.

All 27 validation and all 27 test window coordinates lie beyond the training coordinate range. Generalization requires periodic extrapolation from a continuous trend. Original normalization was fitted on training only, not globally; neither floating-point erasure nor leakage from global normalization explains this result.

**Frozen smoke fixture:** stored history is 8, with 7 observed states. Training stage targets are 102 Benign / 12 Initial Access / 12 Exfiltration; validation and test each contain 17 / 2 / 2. Attack status is generated from hidden sample index `i % 3`, while model-visible node/edge features are random draws conditional on node count. Every training node count includes both benign and attack sequences, and all evaluation node counts occur in training. The generator supplies no intended class-conditioned feature distribution. This is not a proof that finite tensors cannot be memorized or show accidental correlation. Only rollout step 1 has stored ground truth; steps 2–4 permit diversity/legality checks but no accuracy claim.

**Gate/contract questions remain for review:** the original main PDF’s nonzero illegal-transition wording conflicts with the Phase 2 hard mask and the user’s later zero-illegal requirement. This audit applies the explicit user requirement and does not introduce illegal transitions. The integration labels also contain declared Recon-to-Benign resets during training, whereas the original forecast gate has no future reset declarations. No oracle reset metadata was added at evaluation. These issues are flagged; no gate was revised and no replacement experiment is proposed as a pass.

## 4. Real checkpoint selection

**PASS — validation-metric-based in the active training path.** `validate()` runs on `val_loader`; `metrics['f1']` is infiltration F1 at threshold 0.5, not stage F1 or training loss. Selected epochs across the diagnostics are 1, 1, 2, 1, 1, 71, 28, 1 in table order. The epoch-100 checkpoint is audited separately and never substituted for the selected checkpoint.

Exact active `scripts/train.py`, lines **276–289**:

```python
        metrics = validate(model, val_loader, cfg, device, precision)
        rec = {'epoch': ep + 1, 'train': {k: v / count for k, v in sums.items()}, 'val': metrics}
        history.append(rec); print(rec)
        improved = metrics['f1'] > best + cfg['train'].get('min_delta', 0.)
        stale = 0 if improved else stale + 1
        if improved: best = metrics['f1']
        payload = {'model_state': model.state_dict(), 'optimizer_state': optimizer.state_dict(),
                   'scaler_state': scaler.state_dict() if scaler else None, 'config': cfg, 'node_dim': node_dim,
                   'epoch': ep + 1, 'best_metric': best, 'selection_metric': 'val_f1', 'validation': metrics,
                   'class_counts': counts, 'pos_weight': weight, 'normalization': normalization,
                   'normalization_path': str(normalization_path) if normalization else None,
                   'epochs_without_improvement': stale, 'history': history}
        if improved: torch.save(payload, checkpoint)
        torch.save(payload, checkpoint.with_name(checkpoint.stem + '_last.pt'))
```

The historical outer `multisource_audit/CYBERMIND_REAL/scripts/train.py` selects training loss, as documented in the previous root-cause report. That archived path is not invoked here. Validation infiltration F1 selection is verified, but it does not guarantee stage diversity; final checkpoints also fail.

## 5. Main-plan regression and preservation re-audit

| Feature flags | Full suite, CPU and actual CUDA cases | Two-epoch CPU integration |
| --- | --- | --- |
| baseline | 118 passed, 0 skipped | Executed; finite losses and explanations |
| edge_only | 118 passed, 0 skipped | Executed; finite losses and explanations |
| crf_only | 118 passed, 0 skipped | Executed; finite losses and explanations |
| combined | 118 passed, 0 skipped | Executed; finite losses and explanations |

Total: **472 test executions** across four flag contexts. The new weighted-CE integration case passed on CPU and CUDA. Fresh both-off history/evaluation and frozen checkpoint evaluation match Phase 0 within 1e-6. The combined two-epoch CUDA pipeline also completed. These are software/regression passes, not a model diversity pass.

The 100-epoch CUDA run reserved 92,274,688 bytes (88 MiB), below runtime-confirmed 8,518,041,600 bytes. This is the training process’s PyTorch allocator measurement, excluding driver and other processes. All 800 diagnostic epochs have finite recorded train/validation numbers. Negative Gaussian NLL totals are not treated as evidence of stage learning.

All **49** Phase 0 files remain unchanged. Preserved evidence also matches every recorded hash: Phase 3 joint **112 files + 27 local tensors/checkpoints**, rejected balanced fixture **14 + 5**, original root-cause audit **63 + 13**. Preservation of rejected evidence is not reuse as a gate. `configs/gb10_edge_only.yaml`, `configs/gb10_crf_only.yaml` and `configs/gb10_baseline.yaml` are unchanged relative to pre-remediation commit `38d0449`. No Phase 4 work or dataset download occurred.

Evidence is in [examples/phase3_remediation](examples/phase3_remediation/), including predeclared `remaining_plan.json`, per-run configs/history/memory/status/logs, recoverability audits, `preservation.json`, regression JUnit XML and `manifest.json`. Checkpoints and processed tensors remain local and are hash-recorded separately. Original inputs and historical reports are retained.

## 6. Final verdict and remaining work

**Phase 3 exit criteria NOT met.**

The authorized diagnostic plan is complete, but it did not fix the original failure. What remains is a demonstrated model fix on the original non-prototype data: at least two non-Unknown stages and zero illegal transitions independently at each of four rollout steps, with finite training, unchanged regression behavior and valid checkpoint selection. The upstream learning failure still needs a proven remedy; successful analytical label reconstruction and additional confidence are insufficient.

The fixture/transition-contract questions above require review before any gate revision. No replacement gate has been installed. Phase 4 must not begin on this failed result.
