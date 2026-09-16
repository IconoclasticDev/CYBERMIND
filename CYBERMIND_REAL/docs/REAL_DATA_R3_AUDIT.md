# Real-data R3 audit — PASS

Date: 2026-09-16. Scope: epoch-185 synthetic-trained checkpoint evaluated
zero-shot on the frozen R2 real chunk. **R3 exit criteria met because the full
outcome is recorded and qualified, regardless of model quality.** R4 training
requires explicit manual reviewer approval and has not started.

Every result in this report has the required qualifier:
`source: zero-shot, synthetic-trained weights, real-corpus chunk — out-of-distribution test`.

## Checkpoint and preprocessing contract

The evaluated checkpoint is
`examples/phase3_third_round/extended200/checkpoints/combined.pt`, selected at
epoch 185, SHA256
`8a47c8f0f74600e685ba3991a1ae34b3f2618ed47580b760074c089eb1cebf06`.

R2's 60-second prepared graphs use normalization fitted on the real chunk and
therefore do not satisfy this checkpoint's frozen synthetic preprocessing
contract. R3 regenerated a held-out view from the same R2 canonical Parquet
files using the checkpoint's own one-second windows, one-second stride,
three-state histories, and training normalization. This changes no source row,
label, checkpoint weight, fixture, or evaluation gate.

| Contract item | Checkpoint | Observed R3 input | Result |
|---|---:|---:|---|
| Node width | 34 | 34 | PASS |
| Edge width | 27 | 27 | PASS |
| Window | 1 second | 1 second | PASS |
| History | 3 states | 3 states | PASS |
| Normalization fingerprint | `a0bd2ad4e2b6693768deb051042da30801a754d476ed1c44283d92db29dd2d08` | same | PASS |
| Preparation purpose | held-out required | held-out | PASS |

The held-out view contains 41,288 histories. Its local `test.pt` SHA256 is
`96237c2de407f19ee7f5aa90dd6f131dc263d56b367ac88380839f72200c4e65`;
it remains an ignored derived artifact. The active runtime exposed CPU-only
PyTorch, so inference ran on CPU. This changes execution speed, not model math
or the frozen inputs.

## Four-step zero-shot results

The model used four stochastic rollouts, seed 0, no declared stage reset, and
the checkpoint's CRF decoder. There are 41,288 predictions at each step.

| Step | Decoded histogram | Distinct non-Unknown | Unknown | Illegal transitions | Illegal rate | Mean infiltration probability | Mean stage confidence | Mean infiltration variance |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Benign 39,196; Reconnaissance 2,092 | 2 | 0 | 0 | 0.0 | 0.059725 | 0.990684 | 0.001576 |
| 2 | Benign 37,500; Reconnaissance 3,788 | 2 | 0 | 0 | 0.0 | 0.099010 | 0.988381 | 0.004901 |
| 3 | Benign 36,425; Reconnaissance 4,863 | 2 | 0 | 0 | 0.0 | 0.120135 | 0.984584 | 0.008772 |
| 4 | Benign 35,789; Reconnaissance 5,499 | 2 | 0 | 0 | 0.0 | 0.128615 | 0.979855 | 0.012466 |

These numbers are
`source: zero-shot, synthetic-trained weights, real-corpus chunk — out-of-distribution test`.
They are not real-data accuracy metrics because the four future rollout steps
do not have aligned future targets in this artifact.

## OOD finding

The observed three-state histories contain 25,724 Benign, 3,938
Reconnaissance, 33,797 Initial Access, 60,404 Command & Control, and one
Unknown/Ambiguous stage occurrence. The checkpoint nevertheless decodes only
Benign and Reconnaissance at every future step. It never forecasts Initial
Access, Command & Control, or Unknown/Ambiguous.

This is not single-stage collapse under the mechanical diversity definition,
but it is a strong synthetic-to-real generalization limitation. The high mean
stage confidence does not make the predictions accurate or calibrated on real
future targets. No claim of correct kill-chain forecasting follows from this
run.

## Evidence integrity

The summary is `examples/real_data_validation/r3/summary.json`, SHA256
`b8da2e32c835db94c23bd948dabebd4ae27915b22667ba7c0ae5db4a831db73d`.
All 41,288 per-window records, with four stage-probability vectors,
infiltration probabilities, variances, confidence values, and transition flags,
are stored in `per_window_predictions.jsonl.gz`, SHA256
`6ce2c4e776ef2f14b75639bdde028eb2abc1879a08e5766fd8721ef995f7d73a`.

`examples/real_data_validation/r3/output_audit.json`, SHA256
`195c4806fff9901b99c45d2a7f245b7ae7dce0dce6731fe354a2fb3dda690e37`,
read every record and found zero qualifier, step-count, finite-value,
probability-sum, confidence, illegal-transition, sample-count, hash, contract,
or histogram failures.

## Required provenance disclosures

`flow_feature_source: CYBERMIND custom directional packet exporter; 40-column
schema; satisfies the project's 20-field packet-feature contract when verified,
but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter
traffic-statistic columns. No CICFlowMeter feature parity is claimed.`

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.**

## Verdict

**R3 exit criteria met.** The required zero-shot stage, illegal-transition,
infiltration, and confidence outputs are fully recorded with the required OOD
qualifier. The result exposes restricted Benign/Reconnaissance forecasting and
does not establish real-data accuracy. R4 has not started and remains subject
to explicit manual reviewer approval and the overnight-run safeguards.
