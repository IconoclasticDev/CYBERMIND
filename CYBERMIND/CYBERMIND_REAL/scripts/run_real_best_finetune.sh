#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source /venv/main/bin/activate
export PYTHONUNBUFFERED=1

CONFIG="configs/real_best_finetune.yaml"
mkdir -p checkpoints/real_best_finetune results/real_best_finetune

python scripts/train.py --config "$CONFIG" \
  --resume checkpoints/real_best/best.pt --device cuda
python scripts/eval.py --config "$CONFIG" \
  --checkpoint checkpoints/real_best_finetune/best.pt \
  --split val --output results/real_best_finetune/eval_val_fixed.json
python scripts/eval.py --config "$CONFIG" \
  --checkpoint checkpoints/real_best_finetune/best.pt \
  --split test --output results/real_best_finetune/eval_test_fixed.json
