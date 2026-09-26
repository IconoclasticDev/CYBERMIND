#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source /venv/main/bin/activate
export PYTHONUNBUFFERED=1

RAW="data/raw/CIC-IDS-2018"
INTERMEDIATE="data/intermediate/CIC-IDS2018"
COMPATIBLE="data/intermediate/CIC-IDS2018-compatible"
PROCESSED="data/processed_gb10_economy"
STATE="data/manifests/economy_pipeline"
CONFIG="configs/gb10_economy.yaml"
mkdir -p "$RAW" "$INTERMEDIATE" "$PROCESSED" "$STATE" checkpoints results

if [[ ! -f "$STATE/download.complete" ]]; then
  echo "[1/5] Downloading the complete official CSE-CIC-IDS2018 bucket (42 objects, 486140743183 bytes)."
  aws s3 sync --no-sign-request s3://cse-cic-ids2018/ "$RAW/"
  find "$RAW" -type f -printf '%P\t%s\n' | sort > data/manifests/cic2018_downloaded_files.tsv
  touch "$STATE/download.complete"
fi

if [[ ! -f "$STATE/corpus.complete" ]]; then
  echo "[2/5] Normalizing every downloaded official flow CSV. PCAP archives remain intact in raw storage."
  python scripts/build_corpus.py --source CIC-IDS2018 --input "$RAW" --output "$INTERMEDIATE"
  touch "$STATE/corpus.complete"
fi

if [[ ! -f "$STATE/validation.complete" ]]; then
  echo "[3/5] Recording full-corpus validation, then selecting official rows with real endpoints."
  python scripts/validate_dataset.py --input "$INTERMEDIATE" --strict \
    --output data/manifests/cic2018_full_validation.json || true
  mkdir -p "$COMPATIBLE/Processed Traffic Data for ML Algorithms"
  ln -sfn \
    "$ROOT/$INTERMEDIATE/Processed Traffic Data for ML Algorithms/Thuesday-20-02-2018_TrafficForML_CICFlowMeter.parquet" \
    "$COMPATIBLE/Processed Traffic Data for ML Algorithms/Thuesday-20-02-2018_TrafficForML_CICFlowMeter.parquet"
  python scripts/validate_dataset.py --input "$COMPATIBLE" --strict \
    --output data/manifests/cic2018_economy_validation.json
  touch "$STATE/validation.complete"
fi

if [[ ! -f "$STATE/preparation.complete" ]]; then
  echo "[4/5] Building normalized chronological graph sequences from the full flow corpus."
  python scripts/prepare_data.py --config "$CONFIG" --input "$COMPATIBLE" --strict
  python scripts/gpu_preflight.py --config "$CONFIG" \
    --output data/manifests/gb10_economy_preflight.json
  touch "$STATE/preparation.complete"
fi

echo "[5/5] Starting the cost-minimized one-epoch BF16 GPU training run."
python scripts/train.py --config "$CONFIG" --device cuda --epochs 1
touch "$STATE/training.complete"
