# Four-step real-data comparison

Evaluation date: 26 September 2026. Split: `data/processed_stage_expansion/test.pt` (394 sequences). Each method receives the same first 12 observed windows and predicts the same final four unseen windows. Threshold `0.5` was fixed before test evaluation.

| Model | Precision | Recall | F1 | FPR | AP |
|---|---:|---:|---:|---:|---:|
| World model, selected epoch 9 | 0.958042 | 1.000000 | 0.978571 | 0.047745 | 0.993392 |
| Feature-matched per-horizon logistic regression | 0.749088 | 0.998783 | 0.856100 | 0.364721 | 0.982623 |

| Horizon | World F1 | World FPR | Logistic F1 | Logistic FPR |
|---:|---:|---:|---:|---:|
| +1 | 0.981043 | 0.042781 | 0.875264 | 0.315508 |
| +2 | 0.978622 | 0.047872 | 0.859539 | 0.351064 |
| +3 | 0.978520 | 0.047619 | 0.852391 | 0.375661 |
| +4 | 0.976077 | 0.052632 | 0.837782 | 0.415789 |

The world model also records pooled stage accuracy `0.840102`, stage macro-F1 `0.600829`, and illegal-transition rate `0.0`. The evaluated checkpoint does not use the CRF and predates the newly added future-state decoder loss, so the zero illegal-transition rate is an observed result rather than a structural guarantee from that checkpoint.

This comparison supports a result on the current chronological CIC-IDS2018 split only. It does not establish unseen-environment generalization: the data comes from one environment, adjacent sequences overlap, and Lateral Movement and Exfiltration have no training support. Machine-readable predictions, counts, hashes, and per-horizon metrics are in `eval_test_k4.json` and `baseline_test_k4.json`.
