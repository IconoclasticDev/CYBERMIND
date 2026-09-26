# Final Grouped Training Report

## Selection

- Best epoch: 21
- Training termination: `completed_epoch_budget` after epoch 25
- Best checkpoint: `checkpoints/final_grouped/best.pt` (10.69 MB)
- Best SHA-256: `5324902ca017e946af58b41fbd576561553d7c03b532b37ee9255f4a3677cf39`
- Final-state SHA-256: `624eb40612206d5b9fb7ea78685991e18bbb097d43d357b4f28cc3bc7ca27dc7`

## Four-window evaluation

| Split | Precision | Recall | F1 | FPR | AP | Stage macro-F1 |
|---|---:|---:|---:|---:|---:|---:|
| Validation | 0.952096 | 0.843501 | 0.894515 | 0.008914 | n/a | 0.476872 |
| Test | 0.997008 | 0.972993 | 0.984854 | 0.005650 | n/a | 0.244304 |

## Data-integrity statement

- Mixed benign/attack validation: `True`
- Strict chronological capture groups: `True`
- Unseen stage-4 test gate: `True`
- Comprehensive stage-training gate: `False`

Stages 3 and 5 are absent from the available authoritative captures. This run is therefore a leakage-safe binary forecasting and unseen-stage-4 benchmark, not evidence of comprehensive seven-stage performance.
