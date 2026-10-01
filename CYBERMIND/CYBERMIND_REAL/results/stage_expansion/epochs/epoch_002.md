# Epoch 2

## Metrics

| Metric | Training | Validation |
|---|---:|---:|
| Total loss | -0.519673 | -0.059553 |
| Transition loss | -1.408460 | -1.623894 |
| Infiltration loss | 0.320685 | 0.145174 |
| Stage loss | 1.112732 | 2.835711 |
| Calibration loss | 0.047016 | 0.003703 |
| Graph consistency | 0.023339 | 0.005707 |

## Detection on chronological validation

- Precision: `1.000000`
- Recall: `1.000000`
- F1: `1.000000`
- Positive targets: `5865`
- Negative targets: `0`
- Threshold: `0.5`

This validation segment contains no benign targets. Use its recall/F1 and stage loss for training progress; use the final mixed test for precision and false-positive conclusions.
