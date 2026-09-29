#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CONFIG="${1:-configs/final.yaml}"
python scripts/validate_dataset.py --input data/intermediate --strict
python scripts/prepare_data.py --config "$CONFIG" --input data/intermediate --strict
python scripts/run_baseline.py --config "$CONFIG" --split train
python scripts/inspect_env.py
python scripts/visualize_rollout.py --config "$CONFIG" --split val || true
echo "READY: data/processed/{train,val,test}.pt, baseline results, and validation artifacts generated."
