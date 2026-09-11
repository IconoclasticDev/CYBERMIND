#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CONFIG="${CYBERMIND_CONFIG:-configs/gpu_128gb.yaml}"
DOWNLOAD="${CYBERMIND_DOWNLOAD_CIC2018:-0}"
RESUME="${CYBERMIND_RESUME:-}"
EPOCHS="${CYBERMIND_EPOCHS:-0}"
ARGS=(--config "$CONFIG")
[[ "$DOWNLOAD" == "1" ]] && ARGS+=(--download-cic2018)
[[ -n "$RESUME" ]] && ARGS+=(--resume "$RESUME")
[[ "$EPOCHS" != "0" ]] && ARGS+=(--epochs "$EPOCHS")
exec python scripts/launch_training.py "${ARGS[@]}"
