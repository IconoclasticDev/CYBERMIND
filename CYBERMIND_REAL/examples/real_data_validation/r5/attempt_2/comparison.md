# Track A comparison

source: real-chunk validation, pre-Phase-5 — not full-corpus accuracy. This label applies to every number below.

CPU; split test; fixed threshold 0.5; one unseen target window.

| Model | Node / edge / periodic columns | Feature coverage parity | TP | FP | TN | FN | F1 | Precision | Recall | FPR | AP | ROC-AUC |
|---|---|---|---:|---:|---:|---:|---|---|---|---|---|---|
| logistic_regression (node) | 34 / 0 / 0 | no | 32 | 0 | 190 | 209 | 0.234432 | 1.000000 | 0.132780 | 0.000000 | 0.521486 | 0.209129 |
| logistic_regression (node_edge) | 34 / 27 / 0 | no | 28 | 1 | 189 | 213 | 0.207407 | 0.965517 | 0.116183 | 0.005263 | 0.538789 | 0.265604 |
| logistic_regression (feature_matched) | 34 / 27 / 0 | yes; topology summarized | 41 | 0 | 190 | 200 | 0.290780 | 1.000000 | 0.170124 | 0.000000 | 0.713802 | 0.623630 |
| World model, selected epoch 1 | 34 / 27 / 0 | reference | 19 | 0 | 190 | 222 | 0.146154 | 1.000000 | 0.078838 | 0.000000 | 1.000000 | 1.000000 |
| Always Benign | 0 / 0 / 0 | trivial reference | 0 | 0 | 190 | 241 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.559165 | 0.500000 |

**The model loses to the feature-matched baseline on real data.**

Always-Benign comparison: model better on F1 and accuracy; equal FPR (model accuracy 0.484919; always-Benign accuracy 0.440835).
Single-class training fallback invoked: no; training targets were 1143 negative / 556 positive.

- The feature-matched logistic baseline receives every node and edge column plus topology summaries, but fixed aggregation cannot reproduce the world model graph architecture or exact adjacency-message interactions.
- All models receive the same observed windows and predict the same unseen final-window infiltration label.
- One-step infiltration comparison does not establish four-step stage forecasting accuracy.
- Historical whole-sequence baseline numbers are not comparable to this corrected protocol.

FPR = FP / (FP + TN); undefined when the split has no negative examples. Full counts, probabilities, input hashes, feature registry hashes and protocol hash are retained in comparison.json.
