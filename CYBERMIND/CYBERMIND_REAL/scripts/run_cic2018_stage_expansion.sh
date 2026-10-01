#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source /venv/main/bin/activate
export PYTHONUNBUFFERED=1

STATE="data/manifests/stage_expansion_pipeline"
CONFIG="configs/cic2018_stage_expansion.yaml"
mkdir -p "$STATE" results/stage_expansion checkpoints/stage_expansion data/intermediate_stage_expansion

if [[ ! -f "$STATE/rebuild.complete" ]]; then
  python scripts/build_cic2018_stage_expansion.py
  python scripts/validate_dataset.py --input data/stage_expansion/labeled --strict \
    --require-packet-features --output results/stage_expansion/labeled_validation.json
  touch "$STATE/rebuild.complete"
fi

if [[ ! -f "$STATE/canonical.complete" ]]; then
  python scripts/build_corpus.py --source CIC-IDS2018 \
    --input data/stage_expansion/labeled --output data/intermediate_stage_expansion
  python scripts/validate_dataset.py --input data/intermediate_stage_expansion --strict \
    --require-packet-features --output results/stage_expansion/canonical_validation.json
  touch "$STATE/canonical.complete"
fi

if [[ ! -f "$STATE/preparation.complete" ]]; then
  python scripts/prepare_data.py --config "$CONFIG" \
    --input data/intermediate_stage_expansion --strict
  python scripts/verify_stage_expansion.py
  python scripts/gpu_preflight.py --config "$CONFIG" \
    --output results/stage_expansion/gpu_preflight.json
  python scripts/preflight_r4_real_batch.py --config "$CONFIG" \
    --output results/stage_expansion/real_batch_preflight.json
  touch "$STATE/preparation.complete"
fi

if [[ ! -f "$STATE/training.complete" ]]; then
  RESUME_ARGS=()
  if [[ -f checkpoints/stage_expansion/best_last.pt ]]; then
    RESUME_ARGS=(--resume checkpoints/stage_expansion/best_last.pt)
  fi
  python scripts/train.py --config "$CONFIG" --device cuda "${RESUME_ARGS[@]}"
  touch "$STATE/training.complete"
fi

if [[ ! -f "$STATE/evaluation.complete" ]]; then
  python scripts/eval.py --config "$CONFIG" --checkpoint checkpoints/stage_expansion/best.pt \
    --split val --output results/stage_expansion/eval_val_fixed.json
  python scripts/eval.py --config "$CONFIG" --checkpoint checkpoints/stage_expansion/best.pt \
    --split test --output results/stage_expansion/eval_test_fixed.json
  touch "$STATE/evaluation.complete"
fi
