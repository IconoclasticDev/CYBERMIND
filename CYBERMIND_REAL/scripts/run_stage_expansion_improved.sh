#!/bin/bash
set -euo pipefail
cd /workspace/cybermind/CYBERMIND_REAL
STATUS_FILE="results/stage_expansion_improved/status.json"
if [[ -f "$STATUS_FILE" && "${CYBERMIND_FORCE_RETRAIN:-0}" != "1" ]]; then
  STATUS=$(/venv/main/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status",""))' "$STATUS_FILE")
  case "$STATUS" in
    early_stopped|completed_epoch_budget|stopped_on_first_collapse)
      echo "Training already finished with status=$STATUS; refusing automatic retraining. Set CYBERMIND_FORCE_RETRAIN=1 only for an explicitly reviewed new run."
      exit 0
      ;;
  esac
fi
exec /usr/bin/unbuffer -p /venv/main/bin/python scripts/train.py \
  --config configs/cic2018_stage_expansion_improved.yaml --device cuda
