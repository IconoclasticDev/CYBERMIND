# R5 post-hoc leakage and validation-threshold audit

**source: real-chunk validation, pre-Phase-5 — not full-corpus accuracy.** This label applies to every result below.

## Host-identity sanity check

The held-out test split contains 241 positive and 190 negative unseen target windows.

| Botnet Ares victim | Positive targets | Negative targets | Positive histories | Negative histories | Training targets | Seen in train |
|---|---:|---:|---:|---:|---:|---|
| 172.31.69.6 | 241 | 190 | 241 | 190 | 153 | yes |
| 172.31.69.8 | 241 | 190 | 241 | 190 | 154 | yes |
| 172.31.69.10 | 241 | 190 | 241 | 190 | 155 | yes |
| 172.31.69.12 | 241 | 190 | 241 | 190 | 154 | yes |
| 172.31.69.14 | 241 | 190 | 241 | 190 | 159 | yes |
| 172.31.69.17 | 241 | 188 | 241 | 190 | 150 | yes |
| 172.31.69.23 | 241 | 190 | 241 | 190 | 162 | yes |
| 172.31.69.26 | 241 | 190 | 241 | 190 | 138 | yes |
| 172.31.69.29 | 241 | 190 | 241 | 190 | 139 | yes |
| 172.31.69.30 | 241 | 190 | 241 | 190 | 139 | yes |

Target-window host unions overlap on **256** identities (1086 positive-union hosts; 1207 negative-union hosts). Observed-history unions overlap on **309** identities (1139 positive; 1259 negative).

No single observed-history host-presence indicator is a perfect classifier: **0** found. Host-set signatures: 431 unique, 0 occur with both labels, covering 0 samples.

**Host-identity finding:** the ten declared Botnet Ares victim identities do not separate positive from negative windows; every victim occurs in both classes' observed histories and in training. Every test history has a unique complete host-set signature because external endpoints churn, so signature purity is vacuous and is not treated as evidence of host-based generalization.

## Target-construction and single-feature leakage

`y_infiltration` is constructed from corrected labels in the unseen final window. The world model consumes only numeric behavior tensors and topology from `states[:-1]`; labels, targets, attack labels, rule IDs, and IP strings are not model inputs.

The empirical audit tested 244 single-column/history-aggregation combinations. Perfect single-feature separators found: **0**.

| Strongest individual column | Tensor | History aggregation | Test ROC-AUC |
|---|---|---|---:|
| scan_sequential_score | node | mean | 0.999890806 |
| scan_sequential_score | edge | std | 0.999759773 |
| scan_sequential_score | edge | mean | 0.999737934 |
| scan_sequential_score | node | std | 0.996309238 |
| retransmission_count | node | mean | 0.004673509 |

**Leakage finding:** no target, stage, label, corrected-rule, attack-label, or IP-string field enters the model tensor, and no audited individual numeric column is an exact separator. However, mean node `scan_sequential_score` alone has test ROC-AUC 0.999891. The world model's AP/ROC-AUC of 1.0 is therefore a narrow correlate result on this three-day chunk, not evidence that the architecture learned general attack behavior or outperformed a simple behavioral signal.

## Validation-only threshold calibration

Selection rule: maximize validation F1; ties: lower validation FPR, then higher threshold. Test labels were not used. The 428-sequence validation split is extremely imbalanced: 427 positive and 1 negative targets.

| Model / operating point | Threshold | TP | FP | TN | FN | F1 | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|
| World model, fixed | 0.5 | 19 | 0 | 190 | 222 | 0.146154 | 0.000000 |
| World model, validation-calibrated | 0.00600621430203 | 241 | 186 | 4 | 0 | 0.721557 | 0.978947 |
| Feature-matched baseline, fixed | 0.5 | 41 | 0 | 190 | 200 | 0.290780 | 0.000000 |
| Feature-matched baseline, validation-calibrated | 3.23939485525e-11 | 241 | 179 | 11 | 0 | 0.729198 | 0.942105 |

The original 0.5 rows are retained. Calibrated thresholds were selected independently for each model on the 428-sequence validation split and then applied unchanged to the 431-sequence test split.

At the validation-calibrated operating points, the world model has lower test F1 and higher test FPR than the feature-matched baseline. Both thresholds classify almost every test sample positive because validation contains only one negative example; these operating points are valid validation-only selections but weakly constrained for false-positive control.

This post-hoc analysis does not retrain the world model, change checkpoint selection, or replace the R4 gate. R6 has not started.
