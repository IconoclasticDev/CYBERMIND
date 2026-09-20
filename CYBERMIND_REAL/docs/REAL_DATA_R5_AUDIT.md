# R5 Track A real-chunk benchmark audit

Date: 2026-09-20  
Status: complete; R6 not started.  
Scope label for every number in this document: **source: real-chunk validation,
pre-Phase-5 — not full-corpus accuracy**.

## Protocol

Protocol version 3 uses only `states[:-1]`, in chronological order, and predicts
the single unseen `states[-1].y_infiltration` target. The probability threshold
was fixed at 0.5 before execution. Scaling and logistic fitting use the 1,699
training sequences only; the 431 test sequences are held out and contain 190
negative and 241 positive final-window targets.

The three logistic settings are:

1. **Node-only:** per-window means for all 34 node columns.
2. **Node+edge:** per-window means for all 34 node and 27 edge columns.
3. **Feature-matched:** mean, standard deviation, minimum, and maximum for every
   node and edge column, plus node/edge counts, density, self-loop and reciprocal
   ratios, and in/out-degree summaries for every observed window.

The feature-matched baseline receives every feature column available to the
world model and explicit topology summaries. It remains a logistic model over a
fixed aggregate vector, so it cannot reproduce exact adjacency-message
interactions or the graph architecture. This remaining representational
difference is disclosed rather than treated as feature parity of the
architectures.

Protocol SHA256:
`d90f8b7d1560300bc6de77d4f9a5f4648d46fbecabd09116b6069255c416909e`.

## Results

Every value in this table has the scope label stated above.

| Model | TP | FP | TN | FN | F1 | Precision | Recall | FPR | AP | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic, node-only | 32 | 0 | 190 | 209 | 0.234432 | 1.000000 | 0.132780 | 0.000000 | 0.521486 | 0.209129 |
| Logistic, node+edge | 28 | 1 | 189 | 213 | 0.207407 | 0.965517 | 0.116183 | 0.005263 | 0.538789 | 0.265604 |
| Logistic, feature-matched | 41 | 0 | 190 | 200 | 0.290780 | 1.000000 | 0.170124 | 0.000000 | 0.713802 | 0.623630 |
| World model, selected epoch 1 | 19 | 0 | 190 | 222 | 0.146154 | 1.000000 | 0.078838 | 0.000000 | 1.000000 | 1.000000 |
| Always Benign | 0 | 0 | 190 | 241 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.559165 | 0.500000 |

**The model loses to the feature-matched baseline on real data.**

At the fixed 0.5 threshold, the feature-matched baseline detects 41 positive
targets while the world model detects 19, with zero false positives for both.
The F1 difference, world model minus feature-matched baseline, is `-0.144626`.

The world model's AP is effectively 1.0 and ROC-AUC is 1.0, so its probabilities
rank the held-out targets perfectly. Its low thresholded recall shows poor
calibration at the predeclared 0.5 operating point. The protocol does not permit
retuning that threshold after seeing the test labels.

## Always-Benign and single-class checks

Always Benign does not score comparably or better on the primary F1 comparison:
its F1 is 0 versus the model's `0.146154`. Its accuracy is `0.440835` versus the
model's `0.484919`. It ties the model only on FPR at 0. The model therefore has
a measurable advantage over the trivial predictor, but it still misses 222 of
241 positive targets and loses to every logistic baseline on F1.

The single-class fallback was **not invoked**: training targets contain 1,143
negative and 556 positive samples. The retained implementation explicitly uses
a constant training-prior probability if a future training split contains only
one class; metrics and full confusion counts are still produced in that case.

## Retained evidence and hashes

The comparison JSON retains 431 aligned targets and sample-level probabilities
for each of the three baselines, the world model, and Always Benign.

| Artifact/input | SHA256 |
|---|---|
| Epoch-1 checkpoint | `dd5da8fd76118e4b62b0747acc3631b486a404b1d12c15f9a9d79282477cc4aa` |
| Train tensor | `c7422b7f7ccbd9e7ca26438de8cdf60f510aae223637326f5f4dc9ad195f2f5e` |
| Test tensor | `bfcd9396ccb61ba1d3f371739c54c0162463ae20dc63a24d1220db23d4d98935` |
| Normalization | `8f5a295c097ec8a02ac2dc0b8cafa51d416a59b5669143e15fb66bc47c7c2ec5` |
| Comparison JSON | `0ca9466c804b93ca660ac611d81571a63a6ffee2c3b904528f948083683d9406` |
| Comparison Markdown | `aa1731135bd10aa9204b8d6baf7696eb6a4dc9ed3fcaa72a75a12a2e985a3884` |
| Audit JSON | `3131ccdb8aedabce37a4dcea82310a3a0ed24292e58741018f121a1ecd8d4cc7` |
| Focused pytest log | `63898f1f97fb457aa468a42a25864405895682d2cfff6f0beddd27befcc9dd8e` |
| Focused JUnit XML | `99b931f7974c6bff1041f2e46b0a46d90d7167e586bb45bc67f7a43b86d8ed03` |

The focused protocol regression suite reports **20 passed**.

## Limitations and mandatory disclosures

This one-step infiltration benchmark does not establish four-step stage
forecasting accuracy. Feature-column coverage does not make logistic regression
and graph message passing architecturally equivalent. The split is a selected
three-day real chunk, not the complete CIC-IDS2018 corpus. The epoch-1
checkpoint was followed by total validation stage collapse at epoch 21, as
recorded in the R4 audit.

`flow_feature_source: CYBERMIND custom directional packet exporter; 40-column
schema; satisfies the project's 20-field packet-feature contract when verified,
but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter
traffic-statistic columns. No CICFlowMeter feature parity is claimed.`

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.**

R6 has not started and no R6 decision is implied by this result.
