# Final implementation plan — Phase 3 revised exit audit

Verification completed 2026-09-12; audit finalized 2026-09-13 under the user's explicit approval of the revised diversity gate. Base commit: `1aab92b`. **Phase 3 is complete under that approved revision. Phase 4 has not started and requires separate approval.**

The original `FINAL_PLAN_PHASE3_AUDIT.md` and its failed diversity evidence remain unchanged. This audit supplements them; it does not retroactively turn those original single-stage predictions into passes.

## Approved change and work delivered

The user approved replacing the PDF's conflicting nonzero-illegal-rate condition with **zero illegal transitions plus at least two distinct non-Unknown future stages on a separate balanced synthetic fixture**. Existing baseline regression, CPU/GPU gradient, checkpoint, finite-loss and VRAM checks remain required.

Added `examples/phase3_balanced_stage/run_verification.py` and isolated evidence/configuration. The runner generates 192 training, 48 validation and 48 test sequences, balanced across stages 0–5. Each sequence has eight windows, three nodes, 14 node features and seven edge features. Train/validation/test seeds are fixed at 314159, 271828 and 161803. Scenario/window identities and exact feature tensors are checked for disjointness across splits.

The features deliberately encode six artificial observable regimes with independent noise and node/edge variation. Segments maintain a constant regime; campaign-boundary metadata is explicit. These are learnability fixtures, not representations of real network telemetry. No target labels from validation or test are used for training or checkpoint selection.

The combined model uses the existing smoke architecture, optimizer, loss weights, dropout, default batch size of one and seed 42. Both features are enabled. Input/output paths and window timing refer to the separate fixture, and zero dataloader workers limit host RAM. Two epochs ran, totaling 384 optimizer updates over the larger balanced training fixture. The unchanged validation-infiltration-F1 rule selected **epoch 1**; both epochs tied at validation F1=1.0. The last checkpoint is retained separately. There was one experiment, with no seed, hyperparameter or test-result tuning.

No production model, training or evaluation code changed in this revision. The additions are the fixture runner, local output exclusions, evidence and documentation.

## Revised exit evidence

| Check | CPU inference | CUDA inference |
| --- | --- | --- |
| Future-stage counts | Stages 0–5: eight predictions each | Stages 0–5: eight predictions each |
| Distinct non-Unknown future stages | **6** | **6** |
| Unknown predictions | **0** | **0** |
| Illegal transitions | **0 / 48 pairs** | **0 / 48 pairs** |

The gate counts actual future positions only; the observed step-zero stage does not contribute to diversity. Complete decoded sequences match between CPU and CUDA. Both inference paths load the checkpoint's enabled edge features and CRF, including the inferred edge width of seven.

The real two-epoch GPU training process recorded peak allocated memory of **71,837,696 bytes** and peak reserved memory of **73,400,320 bytes (70 MiB)**, below runtime-confirmed capacity of **8,518,041,600 bytes**. The measurement covers the PyTorch allocator, not other applications or driver allocations. All training and validation loss components were finite.

| Loss component | Epoch 1 train | Epoch 2 train | Epoch 2 validation |
| --- | ---: | ---: | ---: |
| Total | 0.681302 | -1.807832 | -2.453514 |
| Stage cross-entropy | 0.751252 | 0.078320 | 0.034194 |
| CRF, unweighted | 2.737557 | 0.115678 | 0.030710 |

Negative total losses are possible because the existing Gaussian transition objective includes a log-variance term; CRF and cross-entropy losses remain positive here. The synthetic infiltration metrics are included in the raw reports but are not real-corpus performance evidence.

## Earlier checks retained

The four-combination matrix from the original Phase 3 work remains valid: **96 tests passed with zero skips in each run, 384 test executions total**, including eight exact joint CPU/CUDA cases. All four CPU pipeline integrations and the original combined GPU checks completed. Fresh both-off training/evaluation and frozen-checkpoint evaluation matched Phase 0 within 1e-6.

The revised runner verified before and after execution that all **49 frozen baseline files**, **112 original Phase 3 evidence files**, and **27 original local tensor/checkpoint files** remain byte-identical. The earlier incomplete audit remains a historical result. The new `examples/phase3_balanced_stage/audit_status.json` records the overall passed status under the approved revision.

## Interpretation and limits

The balanced fixture proves that the combined model can produce more than one stage after a short training run, rather than being structurally forced into a single-stage output. Because class identity is directly represented in artificial prototype coordinates, the result does not establish realistic generalization or intrusion-detection quality.

All fixture segments hold one stage. The existing evaluator tests **one future window**, despite `eval.rollout_steps: 4` in the inherited configuration. These results therefore do not demonstrate multi-step progression or learned campaign resets. The earlier adversarial decoder tests remain the evidence for hard transition constraints and explicit reset handling.

No datasets were downloaded, no GB10 work occurred, and no Phase 4 configuration or diagnostic implementation was started. Full primary-corpus acquisition remains deferred to Phase 5 on GB10. Changes are saved locally only; nothing is pushed remotely.
