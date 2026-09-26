# CYBERMIND — Full and Final Implementation Plan

**Problem statement:** SIH26153<br>
**Project:** Predictive cyber defence through a learned network world model<br>
**Repository:** `IconoclasticDev/cybermind`<br>
**Plan baseline:** 26 September 2026, after commit `97513a0`<br>
**Authoritative status:** This document supersedes earlier execution plans. Historical audit documents remain evidence, but this is the plan to follow from this point.

## 1. Final objective

Deliver an offline system that accepts PCAP or CSV network telemetry, constructs temporal host graphs, learns network-state transitions, forecasts infiltration risk and attack-stage progression for multiple future windows, explains model sensitivity, and compares its performance fairly with logistic regression.

The final claim must be narrower than the evidence. CYBERMIND may claim measured performance on a named split or held-out dataset only when its source, feature coverage, labels, threshold, and confusion counts are recorded. It must not claim detection of stages absent from evaluation, causal containment effects, or unseen-environment generalization without a genuine external test.

Official reference: [SIH26153 problem statement](https://sih.gov.in/sih2026PS#ViewProblemStatement26153).

## 2. Current verified baseline

The following work is complete and will not be repeated unless a later gate fails:

- Dynamic host graphs with node, edge, flow, timing, and packet-derived features.
- Edge-aware GATv2 encoder, causal temporal Transformer, stochastic latent dynamics, infiltration and stage heads, optional constrained CRF, explanations, and counterfactual sensitivity probes.
- Training-only normalization with checkpoint fingerprints and strict inference checks.
- Chronological event splitting with boundary purging.
- Leakage-safe one-step and K-step evaluation.
- Feature-matched, training-only logistic-regression baseline.
- Offline Streamlit input for PCAP, PCAPNG, CSV, and prepared cases.
- Explicit future-state-head training objective and gradient preflight.
- Full automated test suite: 226 tests passed at the plan baseline.
- Two-page architecture document and machine-readable training/evaluation reports.
- Source, reports, configs, manifests, and checkpoints uploaded to GitHub.

Current recommended checkpoint: `checkpoints/stage_expansion/best.pt`, selected at epoch 9. On the existing four-step chronological CIC-IDS2018 test protocol it records F1 `0.978571`, precision `0.958042`, recall `1.000000`, FPR `0.047745`, AP `0.993392`, and stage macro-F1 `0.600829`.

The future-state-loss experiment stopped at epoch 15 and selected epoch 9. It tied the recommended checkpoint on thresholded infiltration metrics and slightly reduced stage macro-F1 to `0.599226`; it remains experimental and does not replace the recommended checkpoint.

## 3. Non-negotiable evidence gaps

Four gaps prevent the current evidence from being called final SIH validation:

1. Validation contains positive targets only, so it cannot select a false-positive operating threshold.
2. Lateral Movement and Exfiltration have no training support in the current stage-expansion corpus.
3. Existing train, validation, and test samples originate from one CIC-IDS2018 environment and overlapping histories; they do not prove external generalization.
4. The legacy custom PCAP exporter uses directional sessions. It does not provide a verified CICFlowMeter-compatible bidirectional packet/flow join.

These gaps must be resolved or explicitly reported. They must never be hidden through synthetic labels, random row splitting, test-threshold tuning, or zero-filled packet fields presented as measured telemetry.

## 4. Execution phases

### Phase A — Freeze reproducibility and protect existing evidence

**Actions**

1. Tag the current recommended and experimental checkpoints by commit and SHA256.
2. Preserve current test reports as immutable reference evidence.
3. Write all new outputs to new directories. Do not overwrite `stage_expansion` or `stage_expansion_improved`.
4. Keep raw and processed datasets off GitHub; retain manifests, source URLs, hashes, label rules, configs, reports, and selected checkpoints.

**Exit gate**

- Every new run has a unique config, output directory, seed, source manifest, and checkpoint lineage.
- Re-running evaluation on the frozen recommended checkpoint reproduces the stored metrics within deterministic tolerance.

**Estimated time:** 20–30 minutes.

### Phase B — Repair the evaluation split before more optimization

**Actions**

1. Repartition events chronologically before sequence construction.
2. Ensure validation and test each contain both benign and attack targets.
3. Preserve a full-window purge at split boundaries.
4. Group capture days or attack episodes so no episode contributes to more than one split.
5. Record sequence counts, class counts, time ranges, source files, stage support, and overlap audit.

If the available chronology cannot produce mixed validation and test populations without leakage, use grouped capture-day validation or nested grouped cross-validation. Do not copy or randomly redistribute overlapping windows.

**Exit gate**

- Validation and test contain at least one true negative and true positive.
- Scenario/day groups are disjoint.
- Split audit passes and is committed before training starts.

**Estimated time:** 1–2 hours with existing prepared events.

### Phase C — Close stage and telemetry coverage

The executable non-regression procedure for stages 3–5 is defined in
[`STAGE_3_TO_5_COVERAGE_IMPLEMENTATION_PLAN.md`](STAGE_3_TO_5_COVERAGE_IMPLEMENTATION_PLAN.md).

**Actions**

1. Inventory CIC-IDS2018 captures against Benign, Reconnaissance, Initial Access, Lateral Movement, Command & Control, Exfiltration, and Unknown/Ambiguous.
2. Add only captures with authoritative scenario, endpoint, and timestamp-based labeling.
3. Add controlled labeled captures for Lateral Movement or Exfiltration only if public CIC-IDS2018 evidence cannot supply them. Keep controlled captures in a separate provenance group.
4. Implement a verified bidirectional extractor for future corpora. It must populate forward/backward bytes, packets, duration and IAT; retain TTL, TCP-window, fragmentation, payload, scan and retransmission features; and pass deterministic reverse-traffic tests.
5. Rebuild graphs and normalization from training data only.

**Exit gate**

- Every reported stage has non-zero train and held-out support, or is marked unsupported and excluded from performance claims.
- Required packet fields have 100% measured coverage for the packet-required experiment.
- Bidirectional extraction and label alignment tests pass.

**Estimated time:** 3–8 hours when captures and labels are locally available; 1–3 days if acquisition or manual labeling is needed.

### Phase D — Run the minimum decisive experiment matrix

Only two teacher runs are mandatory. Extra ablations run only if the two primary runs pass.

1. **Architecture baseline:** edge features off, CRF off.
2. **Combined model:** edge features on, CRF on, future-state loss on.

Both runs must use the same data, split, normalization, width, optimizer family, seed policy, epoch ceiling, early-stopping patience, and checkpoint-selection rule. The combined run may start only after CRF target-transition validation passes.

**Compute-saving rules**

- Use BF16, gradient accumulation, and the measured safe batch size.
- Run one epoch plus preflight before the full budget.
- Stop on non-finite loss, invalid stage transitions, feature-contract mismatch, rollout collapse, or early-stopping patience.
- Never add epochs after validation stops improving.
- Save the selected checkpoint, last checkpoint, five-epoch checkpoints, JSONL epoch metrics, and status record.

**Exit gate**

- Separate baseline and combined checkpoints exist.
- All configured loss components are finite and all intended modules receive gradients.
- Selection uses validation data only.

**Estimated time:** 45–90 minutes on the current GB10 for the current corpus; 2–6 hours for a materially larger rebuilt corpus.

### Phase E — Calibrate and evaluate without test tuning

**Actions**

1. Choose a threshold on mixed-class validation data for a declared target FPR.
2. Freeze the threshold before opening test results.
3. Evaluate K=1 through K=4 and report per-horizon and pooled precision, recall, F1, FPR, AP, confusion counts, stage accuracy, stage macro-F1, illegal-transition rate, and rollout dispersion.
4. Fit the feature-matched logistic baseline using training data only and evaluate it on identical unseen windows.
5. Compare the architecture baseline, combined model, logistic baseline, previous recommended model, and Always-Benign reference.
6. Select a replacement checkpoint only if it improves the declared primary objective without materially damaging stage performance or FPR.

**Primary selection objective**

Maximize four-step test F1 subject to the validation-selected FPR target. Use stage macro-F1 and illegal-transition rate as secondary measures. Test results may confirm a choice but must not choose the threshold.

**Exit gate**

- One signed-off comparison table links to machine-readable reports and hashes.
- A null or negative result retains the current recommended checkpoint.

**Estimated time:** 30–60 minutes after training.

### Phase F — External zero-shot validation

**Actions**

1. Use CTU-13, UNSW-NB15, CIC-IDS2017, or another separately sourced environment strictly as held-out data.
2. Apply primary training normalization without refitting.
3. Report feature-coverage differences. A flow-only external result must be labeled as a different feature setting from the packet-required teacher.
4. Do not silently map incompatible taxonomies into unsupported ATT&CK stages.

**Exit gate**

- At least one external result is reported with source, preprocessing, feature coverage, threshold provenance, counts, and limitations; otherwise the submission explicitly marks external validation pending access.

**Estimated time:** 2–6 hours if data is ready; up to 1–3 days if download and adaptation are required.

### Phase G — Offline deployment validation

**Actions**

1. Test fresh PCAP and CSV uploads end to end with no network access.
2. Verify that incomplete packet telemetry is rejected by packet-required checkpoints.
3. Distill or export the selected teacher only after final model selection.
4. Run CPU-only latency, artifact-size, and numerical-agreement checks.
5. Preserve the full teacher `.pt`; produce an inference-only artifact for deployment.

**Exit gate**

- PCAP/CSV → graph → K-step forecast → explanation works offline.
- CPU inference is below 50 ms on the stated reference machine when feasible.
- Deployment artifact is below 100 MB.
- Every UI claim maps to measured evidence.

**Estimated time:** 1–3 hours.

### Phase H — Final evidence package

**Actions**

1. Update the two-page architecture document with the final selected checkpoint and measured comparison.
2. Produce one final technical report containing data provenance, split audit, parameter count, checkpoint size, latency, per-horizon metrics, baseline comparison, ablation result, failure cases, and limitations.
3. Update README commands to reproduce preparation, training, evaluation, and offline inference.
4. Upload code, configs, manifests, selected checkpoints, epoch reports, final metrics, and documentation to GitHub.
5. Exclude raw/processed datasets, credentials, temporary files, caches, and machine-specific runtime state.

The two-minute video and five-slide presentation are intentionally outside this execution plan because they were excluded from the requested improvement work.

**Exit gate**

- A clean clone can install dependencies, run tests, inspect evidence, and reproduce evaluation when supplied the documented datasets.
- GitHub contains no secrets and no file exceeding platform limits.

**Estimated time:** 1–2 hours after final evaluation.

## 5. Final acceptance matrix

| Requirement | Acceptance evidence |
|---|---|
| Temporal world model | Gaussian transition loss, future-state loss, K-step reports |
| Flow and packet inputs | Feature registry, coverage audit, strict ingestion gate |
| Future infiltration | Validation-frozen threshold and K-step F1/precision/recall/FPR |
| Attack progression | Stage support table, macro-F1, transition legality, CRF ablation |
| Explainability | Stored feature/attention sensitivity with non-causal wording |
| Offline PCAP/CSV interface | End-to-end offline test and lineage export |
| Logistic baseline | Same observed histories, feature registry and per-horizon report |
| Unseen attacks/environment | External held-out report or explicit pending-access limitation |
| Reproducibility | Configs, hashes, seeds, manifests, tests, checkpoints and commands |

## 6. Schedule and completion estimate

If all required captures and labels are already local, the remaining work is approximately **8–16 hours**, including two training runs, evaluation, external testing, deployment checks, and final reporting.

If missing-stage or external datasets require acquisition and manual label validation, completion is approximately **1–3 days**. Network bandwidth and source access dominate this range; adding epochs does not solve those evidence gaps.

## 7. Stop conditions and final model decision

The work stops and the current recommended checkpoint remains final if a new candidate:

- fails provenance, split, packet-coverage, or transition validation;
- improves training loss without improving held-out objectives;
- raises FPR materially at the frozen operating point;
- reduces stage macro-F1 beyond the declared tolerance;
- relies on test-set threshold tuning; or
- cannot reproduce its metrics from committed configuration and lineage records.

The final model is the smallest reproducible checkpoint that satisfies the evidence gates, not the checkpoint trained for the most epochs.
