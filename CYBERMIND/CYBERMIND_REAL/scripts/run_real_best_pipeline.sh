#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source /venv/main/bin/activate
export PYTHONUNBUFFERED=1

STATE="data/manifests/real_best_pipeline"
CONFIG="configs/real_best.yaml"
mkdir -p "$STATE" results/real_best checkpoints/real_best data/intermediate_real_best

if [[ ! -f "$STATE/rebuild.complete" ]]; then
  python scripts/rebuild_audited_real_chunk.py
  touch "$STATE/rebuild.complete"
fi

if [[ ! -f "$STATE/canonical.complete" ]]; then
  python scripts/validate_dataset.py --input data/real_chunk/labeled --strict \
    --require-packet-features --output results/real_best/labeled_validation.json
  python scripts/build_corpus.py --source CIC-IDS2018 \
    --input data/real_chunk/labeled --output data/intermediate_real_best
  python scripts/validate_dataset.py --input data/intermediate_real_best --strict \
    --require-packet-features --output results/real_best/canonical_validation.json
  touch "$STATE/canonical.complete"
fi

if [[ ! -f "$STATE/preparation.complete" ]]; then
  python scripts/prepare_data.py --config "$CONFIG" \
    --input data/intermediate_real_best --strict
  python scripts/gpu_preflight.py --config "$CONFIG" \
    --output results/real_best/gpu_preflight.json
  python scripts/preflight_r4_real_batch.py --config "$CONFIG" \
    --output results/real_best/real_batch_preflight.json
  touch "$STATE/preparation.complete"
fi

if [[ ! -f "$STATE/training.complete" ]]; then
  python scripts/train.py --config "$CONFIG" --device cuda
  touch "$STATE/training.complete"
fi

if [[ ! -f "$STATE/evaluation.complete" ]]; then
  python scripts/eval.py --config "$CONFIG" --checkpoint checkpoints/real_best/best.pt \
    --split val --output results/real_best/eval_val_fixed.json
  python scripts/eval.py --config "$CONFIG" --checkpoint checkpoints/real_best/best.pt \
    --split test --output results/real_best/eval_test_fixed.json
  touch "$STATE/evaluation.complete"
fi
