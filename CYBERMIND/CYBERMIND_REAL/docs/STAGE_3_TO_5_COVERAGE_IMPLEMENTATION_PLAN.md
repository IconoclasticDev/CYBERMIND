# Stage 3–5 Coverage and Non-Regression Implementation Plan

**Project:** CYBERMIND / SIH26153  
**Stages:** 3 — Lateral Movement; 4 — Command & Control; 5 — Exfiltration  
**Champion:** `checkpoints/final_grouped/best.pt`, epoch 21  
**Plan date:** 26 September 2026

## 1. Objective and guarantee

Add genuine training and held-out evidence for stages 3, 4 and 5 while preserving the current infiltration detector. More epochs on the existing data cannot meet this objective because stages 3 and 5 are absent and stage 4 is deliberately absent from training.

The non-regression guarantee applies to the **released checkpoint**, not every experimental run. The epoch-21 champion remains the production model until a challenger passes every frozen legacy gate and every new stage-coverage gate. A failed challenger is retained as an experiment and is never promoted.

## 2. Frozen champion evidence

Do not alter or use these test results to choose hyperparameters:

| Four-window benchmark | F1 | Precision | Recall | FPR | AP | Stage macro-F1 |
|---|---:|---:|---:|---:|---:|---:|
| Mixed validation | 0.894515 | 0.952096 | 0.843501 | 0.008914 | 0.892259 | 0.476872 |
| Chronological unseen-stage-4 test | 0.984854 | 0.997008 | 0.972993 | 0.005650 | 0.998504 | 0.244304 |

Before acquiring or training anything:

1. Record the champion, normalization, split audit and evaluation SHA-256 hashes.
2. Mark the current March 2 C2 capture and test graphs read-only for final evaluation.
3. Write all stage-coverage data, checkpoints and reports to new versioned directories.
4. Keep the current threshold, rollout seed and evaluation code frozen.

## 3. Evidence acquisition

### 3.1 Required independent capture groups

Acquire at least three independently executed capture groups for each stage: one group assigned to training, one to validation and one to sealed testing. Five groups per stage—three train, one validation and one test—are preferred. Split by campaign before windowing; a host, session, campaign or overlapping window must never cross splits.

| Stage | Required evidence | Prohibited shortcut |
|---|---|---|
| 3 — Lateral Movement | A verified compromise followed by movement from one internal host to another, with attacker/victim IPs and exact start/end times | Mapping scans, generic infiltration or use of SMB/RDP/SSH alone to stage 3 |
| 4 — Command & Control | An independent beacon/C2 campaign for training and another independent held-out campaign | Moving any part of the sealed March 2 capture into training |
| 5 — Exfiltration | A verified transfer of controlled data from a compromised host to a controlled external sink, with transfer boundaries and endpoints | Mapping ordinary uploads, high byte counts or protocol names alone to stage 5 |

Every attack capture must include benign background traffic from the same environment. Store capture hash, scenario ID, campaign ID, tool/action log, host roles, endpoint pairs, timestamps, label author and label rule in the manifest. Ambiguous windows remain stage 6; they are never forced into stages 3–5.

### 3.2 Minimum acceptance gate

Data preparation stops unless:

- stages 0 through 5 each have non-zero train, validation and test support;
- every stage 3–5 split contains an independent campaign group;
- required packet features have 100% measured coverage;
- all capture hashes and label intervals validate;
- no scenario, host/session identity or graph-window fingerprint overlaps splits; and
- validation and test both contain benign and malicious targets.

Counts of overlapping 30-second windows are not treated as independent evidence. Reports must include campaign counts alongside window counts.

## 4. Label and model changes

### 4.1 Preserve the existing graph target

Keep the seven-class graph-level stage target for checkpoint compatibility. Replace majority-only labeling with an additional multi-label target when multiple stages occur in one window; do not erase the existing scalar target until a migration test proves compatibility.

### 4.2 Add host-level supervision

Add `node_stage` and `node_attack_mask` targets keyed by host/IP and time window. Train a node-stage head from node embeddings and aggregate its probabilities into the graph explanation. This addresses the current global-label limitation and enables the report to identify which host supports a stage prediction.

The host output is model attribution, not proof of causality. Evaluation must report node-stage precision, recall and macro-F1 only where host-level ground truth exists.

### 4.3 Protect infiltration behavior

Use the epoch-21 checkpoint and its normalization unchanged for the first challengers. Add three safeguards:

1. A replay set stratified across benign and existing stages 1, 2 and 6.
2. Distillation loss that keeps challenger infiltration logits close to the frozen champion on legacy replay samples.
3. Separate optimizer groups with a lower learning rate for shared encoder layers than for new or stage-specific heads.

Do not manufacture missing stages with SMOTE or duplicated windows. Class-balanced sampling may change how often genuine campaign groups are drawn, but all metrics use natural held-out prevalence.

## 5. Minimal training sequence

Only advance when the previous step passes validation gates.

### Challenger A — Head-only adaptation

- Load epoch 21.
- Freeze graph encoder, temporal encoder, dynamics and infiltration head.
- Train graph-stage and node-stage heads on the combined replay/new-stage training set.
- Use BF16, three-epoch minimum, twelve-epoch ceiling and four-epoch patience.

This has the lowest regression risk. If stage 3–5 validation is adequate, stop here.

### Challenger B — Partial unfreeze

- Start from the best Challenger A checkpoint.
- Unfreeze the last temporal block and stage-related projection layers.
- Keep the infiltration head frozen and apply champion-logit distillation.
- Use approximately one-fifth of the head learning rate for shared layers.
- Use a twelve-epoch ceiling and four-epoch patience.

Run this only if head-only adaptation underfits a supported stage.

### Challenger C — Full fine-tune

Run only if Challenger B fails stage coverage while preserving legacy validation. Unfreeze the full model with discriminative learning rates and distillation. Stop immediately on a legacy FPR breach, non-finite loss, stage collapse or four validation checks without improvement.

No run receives extra epochs after patience is exhausted.

## 6. Checkpoint selection

Select candidates using validation only. Rank candidates lexicographically:

1. Pass the legacy validation non-regression gate.
2. Pass non-zero recall for stages 3, 4 and 5.
3. Maximize seven-class validation macro-F1.
4. Maximize worst-stage recall.
5. Prefer the smaller/earlier checkpoint when otherwise tied.

Training loss and binary F1 alone cannot select the stage-expanded model.

## 7. Release gates

### 7.1 Legacy deterministic regression suite

Using the frozen data, threshold, normalization and rollout seed, require:

- validation F1 at least `0.894515` and FPR no greater than `0.008914`;
- final test F1 at least `0.984854`, AP at least `0.998504` and FPR no greater than `0.005650`;
- no new feature-contract, illegal-transition or inference-integrity failure; and
- numerical tolerance no larger than `1e-4` for deterministic comparisons.

The sealed test is opened once, after validation has selected one challenger. A test failure keeps epoch 21 as champion; it does not trigger test-driven tuning.

### 7.2 New comprehensive stage suite

Require:

- non-zero support and recall for every stage 0–5;
- stage macro-F1 of at least `0.60` as the initial acceptance floor;
- worst-stage recall of at least `0.50`;
- no stage 3–5 recall below its frozen stage-only baseline;
- zero illegal decoded transitions unless an explicit campaign reset applies; and
- per-host results for the labeled stage 3–5 hosts.

These are initial engineering gates, not guaranteed outcomes. If no challenger passes, the champion remains deployed and the report identifies the failed stage or domain shift.

## 8. Required implementation artifacts

Add and commit:

- `data/manifests/stage_3_5_v1/` with URLs or capture provenance, hashes and label intervals;
- a strict stage-coverage and group-overlap audit;
- node-stage fields in the graph schema and backward-compatible loader;
- node-stage head and loss with unit/gradient tests;
- frozen replay/distillation training support;
- a stage-aware checkpoint-selection policy;
- configs for Challengers A–C in separate output directories;
- per-epoch reports, selected and last checkpoints, confusion matrices, per-stage metrics and per-host metrics; and
- one champion-versus-challenger decision report.

Raw PCAPs and processed tensors remain outside GitHub. Manifests, source code, configs, hashes, reports and selected checkpoints are pushed.

## 9. Execution order and estimate

| Work | Estimate |
|---|---:|
| Freeze champion and add automated regression gate | 1–2 hours |
| Acquire or execute independent stage 3–5 captures | 1–3 days |
| Validate labels, build manifests and prepare grouped graphs | 4–8 hours |
| Implement node labels/head, replay and distillation | 4–8 hours |
| Run head-only and, if necessary, partial-unfreeze training | 1–3 hours GPU time |
| Final sealed evaluation, report and GitHub publication | 1–2 hours |

Expected elapsed time is **2–4 days**, dominated by obtaining defensible stage 3 and stage 5 evidence. If verified captures and action logs already exist, implementation and training can finish in approximately **10–18 hours**.

## 10. Final decision

Promote a challenger only when all legacy and comprehensive-stage gates pass. Otherwise retain `checkpoints/final_grouped/best.pt` as the released model. This policy guarantees that experimental stage expansion cannot lower the published production scores; it does not claim that every attempted fine-tune will improve them.
