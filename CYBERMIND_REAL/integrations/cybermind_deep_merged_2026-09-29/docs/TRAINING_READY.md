# CYBERMIND — Training-Ready Definition

The repository is considered **training-ready** when these artifacts exist:

```text
data/intermediate/        normalized endpoint-aware parquet/csv
 data/processed/train.pt
 data/processed/val.pt
 data/processed/test.pt
 data/processed/metadata.json
results/baseline_*.json
results/rollout.png (after a trained checkpoint)
configs/gpu_128gb.yaml
```

## Pre-training checklist

1. Raw public data downloaded.
2. Dataset adapter output created in `data/intermediate/`.
3. Strict validation passes: timestamp + endpoints + labels.
4. Graph sequences built with scenario/group split.
5. Logistic baseline runs.
6. `gpu_preflight.py` passes on the 128-GB GPU host.

After step 6, the remaining ML action is `scripts/train.py` with `configs/gpu_128gb.yaml`.

## Scientific constraints

- Never split random rows from the same attack scenario across train/test.
- Keep a held-out attack family/scenario for unseen-attack evaluation.
- Do not call coarse label-to-stage mapping “ground truth ATT&CK annotation.”
- Do not claim counterfactual outputs are causal estimates; label them as simulated/model-based risk changes.
- Report lead time together with F1/precision/recall/AP/FPR.
