# Phase 3 final audit — reviewed selection and extension

**Phase 3 exit criteria met.** Date: 2026-09-13. This verdict applies to the explicitly reviewed Phase 3 scope: unchanged four-step integration diversity/legality gate, approved periodic input representation, approved frozen-fixture mechanical gate and approved validation-only checkpoint policy. Phase 4 has not started and requires separate approval.

The actual training loop selected **epoch 185**. Its validation infiltration F1 is **1.0**, validation stage cross-entropy **0.0095255390**, and it passes the integration gate at **all four forecast steps**. The tolerance remained exactly **0.05** throughout. No test result or final-epoch preference entered selection.

## Authorization and work completed

The user approved Option 2 in `CYBERMIND_Reviewer_Decision_Tolerance.pdf` and the accompanying message: absolute F1 tolerance 0.05, validation stage CE as the lower-is-better tie-breaker, exact sequential pseudocode, and extension beyond epoch 100 if needed. The earlier frozen Option 2 and periodic input decisions remain in effect. [REVIEW_DECISION.md](examples/phase3_third_round/REVIEW_DECISION.md) records the precise scope and the **epoch-200 extension budget fixed before training**, with no subsequent tolerance adjustment.

Implemented `CheckpointSelection` in the real `scripts/train.py` path. The opt-in configuration is `selection_metric: val_f1_stage_band`, `selection_f1_tolerance: 0.05`, `selection_stage_metric: stage`. `stage` maps to the existing validation StageHead CE, not CRF NLL, train loss or test diversity. Existing configurations retain the original `val_f1` default. Protected GB10 configs were not edited; enabling the approved policy in future GB10 configs belongs to the separately approved configuration phase.

Checkpoint payloads now preserve selection state and Python/NumPy/PyTorch RNG state. Resume reconstructs selection from validation history, checks policy/tolerance/metric compatibility, restores RNG, and retains the previously selected model even when the continuation uses another output directory. The selector is independent of edge, CRF and class-balance flags; opting out retains original selection behavior.

## Actual retrospective result and replay

The document correctly excludes epoch 100 but incorrectly predicts epoch 94 remains selected. Applying its exact pseudocode to **all 100 recorded validation epochs selects epoch 98**, with F1 **1.0** and stage CE **0.2919362330**. The complete validation-only selection trace was saved before any new training. Only epochs 94/100 originally had saved weights, so epoch 98 was recovered by deterministic replay; it was never replaced with a nearby available checkpoint.

All 100 replayed train/validation histories match the original within **1e-6**, and every epoch-100 model tensor matches the original **bit for bit**; optimizer state and parameter groups also match exactly. Recovered epoch 98 fails only step 1 of the integration gate. The authorized extension resumed epoch-100 model and optimizer state through epoch 200, retaining the same data, periodic transform, architecture, losses, LR, seed and four-step evaluation protocol. Patience 201 permits the declared budget. Every recorded train/validation loss is finite.

The supplied monotonicity claim is also qualified: validation stage CE rises from 0.291936 at epoch 98 to 0.304556 at epoch 99 before falling to 0.277114 at epoch 100. The extension was an authorized experiment, not a guaranteed result inferred from monotonicity. The 0.05 tolerance is a reviewer-set policy, not a statistically established confidence bound on overlapping synthetic sequences.

## Per-step integration gate

Each row covers 25 original test samples, four rollout trajectories, unchanged seed/protocol and no oracle future resets. Passing requires at least two non-Unknown stages, zero illegal incoming transitions, and fewer Unknowns than samples at every future step independently. Stage IDs 0/1 are Benign/Recon.

| Checkpoint | Step | Distinct known | Illegal transitions | Unknown count | Histogram | Verdict |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| retrospective98 | 1 | 1 | 0 | 0 | {'0': 25} | FAIL |
| retrospective98 | 2 | 2 | 0 | 0 | {'0': 19, '1': 6} | PASS |
| retrospective98 | 3 | 2 | 0 | 0 | {'0': 19, '1': 6} | PASS |
| retrospective98 | 4 | 2 | 0 | 0 | {'0': 19, '1': 6} | PASS |
| selected185 | 1 | 2 | 0 | 0 | {'0': 19, '1': 6} | PASS |
| selected185 | 2 | 2 | 0 | 0 | {'0': 19, '1': 6} | PASS |
| selected185 | 3 | 2 | 0 | 0 | {'1': 13, '0': 12} | PASS |
| selected185 | 4 | 2 | 0 | 0 | {'1': 13, '0': 12} | PASS |
| last200 | 1 | 1 | 0 | 0 | {'0': 25} | FAIL |
| last200 | 2 | 2 | 0 | 0 | {'0': 22, '1': 3} | PASS |
| last200 | 3 | 2 | 0 | 0 | {'0': 19, '1': 6} | PASS |
| last200 | 4 | 2 | 0 | 0 | {'0': 19, '1': 6} | PASS |

The selected epoch 185 passes every step. The epoch-200 last checkpoint fails step 1 and has validation F1 **0.1538461538**, stage CE **0.3690144968**. It is preserved as a failed result and is not shipped in place of the validation-selected model. Independently replaying the approved selector over all 200 validation records reproduces epoch 185; checkpoint metadata and saved state match that decision.

## Exact real-path selection logic

**PASS — validation-metric-based.** The following implementation is the reviewer’s sequential rule; `metrics` comes from validation, and no test-set metric is passed to it. The algorithmic `best_f1` anchor updates only in the branches specified by the reviewer; it is not silently replaced with an unconditional maximum or a retrospective global-band ranking.

`src/cybermind/utils/checkpoint_selection.py`, lines 34–47:

```python
        stage_ce = metrics['stage']
        if not math.isfinite(stage_ce) or stage_ce < 0:
            raise ValueError('Validation stage cross-entropy must be finite and nonnegative.')
        # Literal reviewer pseudocode: do not silently replace with a global-max
        # band, retroactive ranking, or test-set diversity selection.
        if f1 > self.best_f1 + self.tolerance:
            self.best_f1, self.best_stage_ce, self.selected_epoch = f1, stage_ce, epoch
            return True
        elif f1 >= self.best_f1 - self.tolerance:
            if stage_ce < self.best_stage_ce:
                self.best_stage_ce, self.selected_epoch = stage_ce, epoch
                self.best_f1 = max(self.best_f1, f1)
                return True
        return False
```

`scripts/train.py`, lines 305–323, real validation and save path:

```python
        metrics = validate(model, val_loader, cfg, device, precision)
        rec = {'epoch': ep + 1, 'train': {k: v / count for k, v in sums.items()}, 'val': metrics}
        history.append(rec); print(rec)
        improved = selection.update(ep + 1, metrics)
        stale = 0 if improved else stale + 1
        best = selection.best_f1
        import random, numpy as np
        payload = {'model_state': model.state_dict(), 'optimizer_state': optimizer.state_dict(),
                   'scaler_state': scaler.state_dict() if scaler else None, 'config': cfg, 'node_dim': node_dim,
                   'epoch': ep + 1, 'best_metric': best, 'selection_metric': selection.metric, 'validation': metrics,
                   'selection_state': selection.state_dict(),
                   'rng_state': {'python': random.getstate(), 'numpy': np.random.get_state(),
                                 'torch': torch.get_rng_state(),
                                 'cuda': torch.cuda.get_rng_state_all() if device.type == 'cuda' else None},
                   'class_counts': counts, 'pos_weight': weight, 'normalization': normalization,
                   'normalization_path': str(normalization_path) if normalization else None,
                   'epochs_without_improvement': stale, 'history': history}
        if improved: torch.save(payload, checkpoint)
        torch.save(payload, checkpoint.with_name(checkpoint.stem + '_last.pt'))
```

## Regression, resume and preservation

| Flag context | Full suite (CPU + actual CUDA cases) | CPU integration |
| --- | --- | --- |
| baseline | 145 passed, 0 skipped | Completed, finite losses and explanations |
| edge_only | 145 passed, 0 skipped | Completed, finite losses and explanations |
| crf_only | 145 passed, 0 skipped | Completed, finite losses and explanations |
| combined | 145 passed, 0 skipped | Completed, finite losses and explanations |

**580 test executions**, zero skips across four flag contexts. Fourteen focused selection tests cover strict/inclusive band boundaries, outside-band rejection, exact anchor semantics, invalid metrics/config and legacy min-delta behavior. Fresh both-off history/evaluation and frozen-checkpoint evaluation retain Phase 0 parity within 1e-6. The combined CUDA pipeline completes with finite losses below device memory capacity. An initial automatic approval-service usage-limit rejection prevented launch; after checking the local-only command and the user’s continuation instruction, the retry was approved and the actual required checks completed.

A separate four-epoch uninterrupted-versus-two-plus-two resumed run has matching histories within 1e-6, **bitwise-equal selected and last model tensors**, and identical selection state. This verifies actual training continuity, not just selector arithmetic.

The approved frozen mechanical gate was reverified on both original checkpoints: zero illegal transitions at all four steps, finite positive supervised CE/CRF losses and nonzero StageHead gradients. The fixture remains unchanged and no frozen diversity requirement was reintroduced.

All preserved evidence matches recorded hashes: Phase 0 **49 files**; original Phase 3 **112 + 27** evidence/local tensor files; rejected balanced fixture **14 + 5**; root-cause **63 + 13**; first remediation **187 + 44**; second escalation **114 + 27**. Historical source hashes describe their original revisions; the new manifest records intentionally changed active training code. Protected `configs/gb10_*.yaml` and `scripts/make_synthetic.py` are unchanged.

## Final completion audit

| Requirement | Evidence / verdict |
| --- | --- |
| Fixed reviewer tolerance and stage-CE tie-breaker in real training | PASS: config 0.05; literal sequential selector; no test-based ranking |
| Existing validation history re-scored honestly | PASS: epoch 98, complete trace; document’s epoch-94 prediction corrected |
| Exact selected checkpoint independently evaluated | PASS: recovered 98 failure recorded; selected extended epoch 185 passes steps 1–4 |
| Authorized continuation on original data | PASS: first-100 parity, saved-RNG resume, 200 finite epochs, unchanged input hashes |
| Reviewed frozen scope | PASS: mechanical gate retained; no regeneration |
| Four-flag CPU/CUDA and legacy regression | PASS: all suites, actual CUDA pipeline, checkpoint/baseline and resume parity |
| Audit, checklist and provenance | PASS: this report, decision record, raw logs/paths and manifest |
| Phase 4 prohibition | Satisfied: no Phase 4 work; separate approval required |

**Phase 3 exit criteria met.** The passing checkpoint is `examples/phase3_third_round/extended200/checkpoints/combined.pt` (**epoch 185**), not `combined_last.pt`. This is laptop synthetic verification under the recorded reviewer decisions, not evidence of real-corpus accuracy or GB10 deployment readiness. Full corpus acquisition remains deferred to Phase 5.
