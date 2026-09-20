# R4 second-attempt audit

Date: 2026-09-20  
Authorization: explicit reviewer approval after option (c) implementation review.  
Final verdict: **R4 exit criteria met under the reviewed real-chunk protocol.**

## Frozen R4.1 configuration

The run used `configs/real_chunk_r4_attempt2.yaml`, SHA256
`e0870db82c1eb78d41cb560f5048f6989541c48eb3badde7f1a0f0f7602b8828`.
It differs from the reviewed option-(c) configuration only in isolated
attempt-2 output paths, which preserve the prior attempt.

| Item | Frozen value |
|---|---|
| Data | `data/processed_real_chunk_r4_option_c` |
| Split | 1,699 train / 428 validation / 431 held-out test sequences |
| Seed | 42 |
| Epoch budget | 50 |
| GPU / precision | RTX 5060 Laptop GPU / bf16 |
| Batch | 4; gradient accumulation 4; effective batch 16 |
| Selection | validation infiltration F1 with fixed 0.05 band; lower validation stage cross-entropy tie-break inside the band |
| Threshold | 0.5 |
| Early-stopping patience | 20 |
| Checkpoints | every epoch, selected-best, and last |
| Collapse monitor | validation split, four steps, every epoch from epoch 1, stop on first collapsed step |

Patience 20 gives this 1,699-sequence training chunk 40% of the 50-epoch
budget to improve, while avoiding the synthetic run's known-too-short default
of 10.

## Training outcome

Training started at 2026-09-20 19:39:32 +05:30. Epochs 1–20 completed without
meeting the collapse stop. At epoch 21, every validation rollout step decoded
all 428 samples as Benign. The loop persisted the epoch checkpoint, metrics,
history, and stop status, then stopped immediately. No automatic retry or
alternate checkpoint substitution occurred.

| Validation step at epoch 21 | Histogram | Distinct non-Unknown | Unknown | Illegal | Collapse |
|---|---|---:|---:|---:|---|
| 1 | Benign 428 | 1 | 0 | 0 | Yes |
| 2 | Benign 428 | 1 | 0 | 0 | Yes |
| 3 | Benign 428 | 1 | 0 | 0 | Yes |
| 4 | Benign 428 | 1 | 0 | 0 | Yes |

All 21 attempted epoch checkpoints are preserved. The validation policy selected
epoch 1: validation F1 `0.7896253602305475`, validation stage CE
`5.603485157556623`. The selected checkpoint SHA256 is
`dd5da8fd76118e4b62b0747acc3631b486a404b1d12c15f9a9d79282477cc4aa`.

The epoch-21 collapse is material evidence of training instability. The pass
below applies to the validation-selected epoch-1 checkpoint; it does not mean
that later training converged to a stable diverse solution.

## Held-out four-step gate

The selected epoch-1 checkpoint was evaluated once against all 431 held-out
test sequences with four rollouts, seed 0, and the unchanged strict transition
policy.

| Step | Decoded histogram | Distinct non-Unknown | Illegal transitions | Unknown count | Verdict |
|---|---|---:|---:|---:|---|
| 1 | Benign 429; Initial Access 2 | 2 | 0 | 0 | PASS |
| 2 | Benign 429; Initial Access 2 | 2 | 0 | 0 | PASS |
| 3 | Benign 429; Initial Access 2 | 2 | 0 | 0 | PASS |
| 4 | Benign 429; Initial Access 2 | 2 | 0 | 0 | PASS |

The frozen gate requires at least two distinct non-Unknown stages, zero illegal
transitions, and fewer Unknown predictions than samples at every step. All four
steps pass. This is a narrow pass at the minimum diversity threshold: only two
of 431 predictions at each step are non-Benign.

Gate evidence SHA256:
`654b56cbc0473efae5504d5b0ab9c4af64df5e49e52841fde112e98dd17feb6a`.

The complete artifact manifest records the isolated config, durable logs,
history, status, selected/last checkpoints, and all 21 epoch checkpoints.
Manifest SHA256:
`79bfe788fc4a8d5ff531887338f580bdece1767426638418b96ec84e89df140d`.

## Scope and disclosures

R5 has not started. This R4 result does not authorize R5, R6, the main-plan
Phase 5 run, or the GB10 window.

`flow_feature_source: CYBERMIND custom directional packet exporter; 40-column
schema; satisfies the project's 20-field packet-feature contract when verified,
but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter
traffic-statistic columns. No CICFlowMeter feature parity is claimed.`

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.**
