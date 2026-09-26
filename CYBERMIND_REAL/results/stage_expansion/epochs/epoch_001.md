# Epoch 1

## Metrics

| Metric | Training | Validation |
|---|---:|---:|
| Total loss | 1.211059 | 1.530641 |
| Transition loss | -0.481917 | -1.661245 |
| Infiltration loss | 0.824605 | 1.889438 |
| Stage loss | 1.656640 | 2.486544 |
| Calibration loss | 0.176411 | 0.293761 |
| Graph consistency | 0.047687 | 0.004239 |

## Detection on chronological validation

- Precision: `1.000000`
- Recall: `0.189429`
- F1: `0.318521`
- Positive targets: `5865`
- Negative targets: `0`
- Threshold: `0.5`

This validation segment contains no benign targets. Use its recall/F1 and stage loss for training progress; use the final mixed test for precision and false-positive conclusions.
