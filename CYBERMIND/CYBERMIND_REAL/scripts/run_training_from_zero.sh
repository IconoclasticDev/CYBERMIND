#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONUNBUFFERED=1
ARGS=(--config "${CYBERMIND_CONFIG:-configs/gb10_full.yaml}")
if [[ "${CYBERMIND_DOWNLOAD_CIC2018:-1}" == "1" ]]; then ARGS+=(--download-cic2018); else ARGS+=(--no-download-cic2018); fi
if [[ -n "${CYBERMIND_RESUME:-}" ]]; then ARGS+=(--resume "$CYBERMIND_RESUME"); fi
if [[ -n "${CYBERMIND_EPOCHS:-}" ]]; then ARGS+=(--epochs "$CYBERMIND_EPOCHS"); fi
python scripts/launch_training.py "${ARGS[@]}"
