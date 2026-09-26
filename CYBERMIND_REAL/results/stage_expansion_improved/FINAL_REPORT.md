# Future-state-loss training report

Training stopped normally at epoch 15 after six epochs without a better selected checkpoint. The validation policy selected epoch 9. All 15 epochs used the repaired explicit future-state loss with weight `0.25`; its training loss decreased from `0.182626` at epoch 1 to `0.010401` at epoch 15.

## Four-step mixed-test result

| Model | Precision | Recall | F1 | FPR | AP | Stage accuracy | Stage macro-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Repaired future-state model | 0.958042 | 1.000000 | 0.978571 | 0.047745 | 0.993403 | 0.836294 | 0.599226 |
| Previous selected model | 0.958042 | 1.000000 | 0.978571 | 0.047745 | 0.993392 | 0.840102 | 0.600829 |
| Feature-matched logistic baseline | 0.749088 | 0.998783 | 0.856100 | 0.364721 | 0.982623 | n/a | n/a |

The repaired model ties the previous model on thresholded infiltration metrics, changes AP only negligibly, and slightly reduces stage performance. It therefore does not replace the previous selected checkpoint. The result shows that training the previously disconnected future-state head is technically correct but does not improve the current downstream heads on this dataset.

Threshold calibration was not performed because validation contains 5,865 positive targets and zero negatives. Choosing an FPR operating point from that split would be invalid. The fixed predeclared threshold of `0.5` is retained.

The same limitations remain: a single CIC-IDS2018 environment, overlapping adjacent histories, and no training support for Lateral Movement or Exfiltration. External-environment and missing-stage evidence are still required before making generalization claims.
