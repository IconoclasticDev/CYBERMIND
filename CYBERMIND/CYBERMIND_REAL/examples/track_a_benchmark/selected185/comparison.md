# Track A comparison

synthetic verification only; not a real-data benchmark. The model passes under the reviewed protocol on synthetic verification data.

CPU; split test; fixed threshold 0.5; one unseen target window.

| Model | Node / edge / periodic columns | Feature coverage parity | F1 | Precision | Recall | FPR | AP | ROC-AUC |
|---|---|---|---|---|---|---|---|---|
| logistic_regression | 34 / 0 / 0 | no | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.328259 | 0.552632 |
| logistic_regression | 34 / 27 / 0 | no | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.328259 | 0.552632 |
| logistic_regression | 34 / 27 / 2 | yes (pooling discards topology) | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 |
| World model, selected epoch 185 | 34 / 27 / 2 | reference | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 |

- Feature coverage parity does not equal architecture parity: pooled baseline discards graph topology.
- All models receive the same observed windows and predict the same unseen final-window infiltration label.
- One-step infiltration comparison does not establish four-step stage forecasting accuracy.
- Historical whole-sequence baseline numbers are not comparable to this corrected protocol.

FPR = FP / (FP + TN); undefined when the split has no negative examples. Full counts, probabilities, input hashes, feature registry hashes and protocol hash are retained in comparison.json.
