# Phase 3 second escalation audit

**Phase 3 exit criteria NOT met.** Date: 2026-09-13. Phase 4 has not started and remains closed pending review.

The authorized Option 2 scope change and diagnostic #6 were executed. The original frozen fixture passes its reviewed mechanical gate. Periodic features substantially improve the original integration model: epoch 100 passes all four diversity/legality checks. However, the unchanged validation-infiltration-F1 rule selects **epoch 94**, which fails diversity at steps 1–3. Epoch 100 has not been substituted for the selected checkpoint.

## Authorization and scope

The user supplied `CYBERMIND_Frozen_Fixture_Gate_Decision.pdf` and said **“execute this plan immidiately”** after the explicit decision request. This instruction is recorded as approval to execute its recommended Option 2 engineering path, including Tasks A and B. [REVIEW_DECISION.md](examples/phase3_second_escalation/REVIEW_DECISION.md) records the source, exact user instruction, scope and retained constraints. This is an explicit recorded gate revision for the frozen fixture only; historical failed results remain unchanged.

## Task A — reviewed frozen-fixture gate

**PASS.** The fixture is unchanged. `scripts/make_synthetic.py`, its tensors, labels and topology were not regenerated. The active reviewed evaluation is `examples/phase3_second_escalation/frozen_gate.py`; old root-cause and remediation reports retain their original failed diversity flags for provenance. No integration result uses this scoped evaluator.

The gate requires zero illegal incoming transitions independently at steps 1–4 and finite train/validation losses. Non-degenerate supervised loss is operationalized as positive StageHead CE and CRF NLL, with finite nonzero StageHead gradient evidence. It does not require nonnegative total Gaussian NLL or diverse predictions. CPU/CUDA CRF tests, adversarial masking and baseline regression remain required.

Original first-batch CE is **2.0661387444**, CRF NLL **11.7224330902**, total loss **10.4532356262**. Weighted StageHead gradient norms are **1.0431246758** (CE) and **7.7089576721** (CRF). Both selected and last original frozen checkpoints have zero illegal transitions at all four steps. Existing original evidence was evaluated without further frozen training.

The generator record in `examples/phase3_remediation/frozen_recoverability.json` documents random features without intended class-conditioned signal. This supports limiting the fixture to mechanical/regression checks. The PDFs’ claim that diversity is mathematically impossible is not adopted: diverse output is not label accuracy. The reviewed scope decision, not an impossibility claim, authorizes this change.

## Task B — periodic-feature diagnostic #6

Original integration data, chronological splits, labels, topology, normalization and all 34 raw node coordinates remain unchanged. A default-off model input module appends sine and cosine channels from each node’s existing `x[:,2]`. The graph encoder receives 36 columns; all other architectural dimensions, CRF masks and losses are unchanged. Effective inputs change as authorized; no claim is made that the augmented representation is identical to old model inputs.

Constants are fitted from original training windows only and persisted in config/checkpoint buffers: `slope=0.02793721242224979`, `intercept=-1.7181385639683615`, `period=4`. `angle = 2*pi*((x[:,2]-intercept)/slope)/4`. Period 4 is specified by the escalation and supported by prior training-only analysis. Validation/test labels, scenario IDs and future reset declarations do not enter the transform. The transform is applied through `WorldModel.encode_state` in both training and inference; raw tensors are never edited.

CPU-only training: seed 42, 100 epochs / 400 optimizer updates, LR 0.001, batch 16, accumulation 2, patience 101, same original loss coefficients and validation infiltration F1 checkpoint selection. Both checkpoints were loaded through the actual model/config path and evaluated with the unchanged `examples/phase3_root_cause/inspect_rollouts.py`, four trajectories and four future steps.

| Checkpoint | Step | Distinct known | Illegal transitions | Unknown count | Decoded histogram | Result |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| selected, epoch 94 | 1 | 1 | 0 | 0 | {'0': 25} | FAIL |
| selected, epoch 94 | 2 | 1 | 0 | 0 | {'0': 25} | FAIL |
| selected, epoch 94 | 3 | 1 | 0 | 0 | {'0': 25} | FAIL |
| selected, epoch 94 | 4 | 2 | 0 | 0 | {'0': 19, '1': 6} | PASS |
| last, epoch 100 | 1 | 2 | 0 | 0 | {'0': 19, '1': 6} | PASS |
| last, epoch 100 | 2 | 2 | 0 | 0 | {'0': 19, '1': 6} | PASS |
| last, epoch 100 | 3 | 2 | 0 | 0 | {'0': 13, '1': 12} | PASS |
| last, epoch 100 | 4 | 2 | 0 | 0 | {'1': 13, '0': 12} | PASS |

Each row covers 25 original test samples. The exact requirement remains at least two non-Unknown stages, fewer Unknowns than samples, and zero illegal transitions **at each step**. No aggregation across steps, hard-mask relaxation, prototype replacement or test-based checkpoint substitution occurred.

## What improved and what remains

Pre-CRF maximum across-sample logit SD at epoch 100 is **0.666319, 1.378142, 2.440859, 3.887065** at steps 1–4, versus **0.000561, 0.000427, 0.000266, 0.000420** after 100 epochs without periodic input. Thus the feature intervention produces genuinely varying learned emissions, and the epoch-100 forecast passes the full gate on the original non-prototype data. This is stronger than the preceding diagnostics.

The selection mismatch is measured: epoch 94 validation infiltration F1 is **1.0**; epoch 100 is **0.9230769231**. Validation stage CE improves from **0.3522926128** to **0.2771137202**, but the active selector does not optimize stage CE or four-step stage diversity. The model selected by the required real training protocol therefore remains an integration-gate failure. The following exact code is unchanged:

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

Active `scripts/train.py` lines 276–289: **PASS**, validation-metric-based; the metric is infiltration F1, not training loss. This policy was not changed.

## Verification and preservation

| Flag context | Full suite | CPU integration |
| --- | --- | --- |
| baseline | 131 passed, 0 skipped | Completed with finite losses and explanations |
| edge_only | 131 passed, 0 skipped | Completed with finite losses and explanations |
| crf_only | 131 passed, 0 skipped | Completed with finite losses and explanations |
| combined | 131 passed, 0 skipped | Completed with finite losses and explanations |

**524 test executions** across four contexts. Focused periodic tests cover unchanged raw channels, extrapolation across periods, finite gradients, invalid constants, checkpoint configuration compatibility and default-off initialization. The scoped frozen gate rejects illegal transitions, missing steps, NaN losses, zero supervised loss and zero gradients. Fresh both-off and frozen-checkpoint evaluation/history match Phase 0 within 1e-6. The combined CUDA pipeline also completes below device memory capacity.

Preserved hashes: Phase 0 **49 files**; Phase 3 joint **112 evidence + 27 local tensor/checkpoint files**; rejected balanced fixture **14 + 5**; root-cause audit **63 + 13**; first remediation **187 + 44**. Source/report hashes in historical manifests describe their historical revisions; intentionally changed active model/config source is recorded in the new manifest. Original evidence files are unchanged.

Complete evidence, including per-step raw emissions, transition matrices and argmax predictions, lives in [examples/phase3_second_escalation](examples/phase3_second_escalation/). No protected GB10 configs, Phase 4 work or new dataset acquisition were involved.

## Final verdict

**Phase 3 exit criteria NOT met.**

The frozen fixture passes its approved revised scope. Diagnostic #6 establishes an all-four-step passing epoch-100 model, but the unchanged production selection rule keeps a failing epoch-94 model. Remaining work is to obtain an integration-gate pass for the checkpoint selected by the authorized protocol. Selecting epoch 100 because it passed test evaluation would be a post-hoc substitution and is not done here. Any proposal to change selection must be validation-only, specified before another run, and reviewed as a training-protocol change; the integration exit gate must remain intact. Phase 4 remains closed pending review.
