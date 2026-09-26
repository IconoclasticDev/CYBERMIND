#!/bin/bash
set -euo pipefail

cd /workspace/cybermind/CYBERMIND_REAL

/venv/main/bin/python scripts/train.py \
  --config configs/cic2018_final_grouped.yaml --device cuda

/venv/main/bin/python scripts/eval.py \
  --config configs/cic2018_final_grouped.yaml \
  --checkpoint checkpoints/final_grouped/best.pt \
  --split val --horizon 4 --output results/final_grouped/eval_val_k4.json >/dev/null

/venv/main/bin/python scripts/eval.py \
  --config configs/cic2018_final_grouped.yaml \
  --checkpoint checkpoints/final_grouped/best.pt \
  --split test --horizon 4 --output results/final_grouped/eval_test_k4.json >/dev/null

/venv/main/bin/python scripts/write_final_grouped_report.py

cd /workspace/cybermind
git add \
  CYBERMIND_REAL/configs/cic2018_final_grouped.yaml \
  CYBERMIND_REAL/scripts/run_final_grouped_training.sh \
  CYBERMIND_REAL/scripts/write_final_grouped_report.py \
  CYBERMIND_REAL/results/final_grouped \
  CYBERMIND_REAL/checkpoints/final_grouped/best.pt \
  CYBERMIND_REAL/checkpoints/final_grouped/best_last.pt

if ! git diff --cached --quiet; then
  git commit -m "Train leakage-safe grouped CIC-IDS2018 model"
  git push origin HEAD
fi
