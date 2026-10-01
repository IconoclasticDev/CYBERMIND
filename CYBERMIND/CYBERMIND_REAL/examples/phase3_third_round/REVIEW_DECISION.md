# Third-round reviewed training protocol

Authorization: the user's supplied `CYBERMIND_Reviewer_Decision_Tolerance.pdf` and explicit accompanying decision approve Option 2 with **absolute F1 tolerance 0.05**, **validation stage cross-entropy, lower is better**, and the exact sequential pseudocode. The user additionally authorizes extending the same CPU training run beyond epoch 100 and forbids changing 0.05 after seeing results. Phase 4 remains closed.

The concrete extension budget is fixed at **epoch 200** before extension results are observed. The existing seed, raw dataset, periodic feature representation, losses, optimizer and four-step integration gate are retained. Patience is 201 to permit the declared budget. The extension resumes original model/optimizer state after a verified 100-epoch replay, with saved RNG state. It is not a hyperparameter sweep.

Named configuration: `train.selection_metric: val_f1_stage_band`, `train.selection_f1_tolerance: 0.05`, `train.selection_stage_metric: stage`. `stage` is the existing validation StageHead cross-entropy field; no test metric enters selection. The default remains `val_f1` for existing configurations.

The implementation follows the reviewer pseudocode literally. Its `best_f1` is an algorithmic anchor updated only on the specified selection branches; it is not an unconditional maximum of every observed F1. No alternate global-band ranking or candidate pool is substituted. This supersedes the earlier preflight's generic global-band retention discussion.

## Verified corrections to the supplied narrative

- Applying the exact rule to **all 100 validation records selects epoch 98**, not epoch 94. Epoch 100 is excluded. This result was obtained before new training or new test evaluation.
- The actual recorded epoch-94 validation stage CE is **0.3522926128**, not 0.352926.
- Stage CE is not strictly monotone at the end: epoch 98 is **0.2919362330**, epoch 99 **0.3045561266**, epoch 100 **0.2771137202**. The authorized extension proceeds as an experiment, not a guarantee inferred from monotonicity.
- The tolerance is the reviewer's policy choice; this audit does not establish 0.05 as a calibrated statistical confidence bound. The synthetic validation sequences overlap in time and are not independent observations.

## Checklist

- [x] Record exact tolerance, metric, sequential rule and extension budget before applying new training.
- [x] Apply rule to existing validation history: selected epoch 98; retain complete selection trace.
- [x] Implement opt-in real-path selection, matching resume parameters, selection-history reconstruction and RNG checkpointing.
- [x] Focused policy tests: 14 passed, including boundaries, outside-band rejection and default-policy compatibility.
- [x] Recover missing epoch-98 weights; all 100 histories match within 1e-6 and original/replayed epoch-100 model tensors match bit for bit.
- [x] Evaluate recovered epoch 98: fails step 1, passes steps 2–4.
- [x] Extend to epoch 200; selected epoch 185 passes all four steps. Last epoch 200 fails step 1 and is retained separately.
- [x] Verify interrupted/uninterrupted model parity and four-flag CPU/CUDA regressions: 580 test executions, zero skips.
- [x] Verify preservation and publish `PHASE3_FINAL_AUDIT.md`: Phase 3 exit criteria met under reviewed scope. Phase 4 awaits separate review.
