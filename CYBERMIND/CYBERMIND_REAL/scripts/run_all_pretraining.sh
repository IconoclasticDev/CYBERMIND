#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
python scripts/readiness_check.py
if [[ "${DOWNLOAD_KNOWLEDGE:-0}" == "1" ]]; then python scripts/download_public_sources.py; fi
python scripts/build_corpus.py --source CIC-IDS2018 --input data/raw/CIC-IDS-2018 --output data/intermediate/CIC-IDS2018
python scripts/validate_dataset.py --input data/intermediate --strict
python scripts/prepare_data.py --config configs/gpu_128gb.yaml --input data/intermediate --strict
python scripts/run_baseline.py --processed data/processed --split val
python scripts/run_baseline.py --processed data/processed --split test
python scripts/gpu_preflight.py --config configs/gpu_128gb.yaml

echo '==============================================='
echo 'PRE-TRAINING PIPELINE COMPLETE'
echo 'Only model training remains:'
echo '  python scripts/train.py --config configs/gpu_128gb.yaml'
echo '==============================================='
