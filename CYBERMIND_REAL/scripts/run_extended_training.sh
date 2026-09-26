#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source /venv/main/bin/activate
export PYTHONUNBUFFERED=1

CONFIG="configs/gb10_economy.yaml"
CHECKPOINT="checkpoints/best_gb10_economy_last.pt"
TARGET_EPOCHS="${CYBERMIND_TARGET_EPOCHS:-50}"

if [[ ! -s "$CHECKPOINT" ]]; then
  echo "Resume checkpoint is missing: $CHECKPOINT"
  exit 2
fi

python scripts/gpu_preflight.py --config "$CONFIG" \
  --output data/manifests/gb10_economy_extended_preflight.json
python scripts/train.py --config "$CONFIG" --device cuda \
  --resume "$CHECKPOINT" --epochs "$TARGET_EPOCHS"
touch data/manifests/economy_pipeline/extended_training.complete
