#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source /venv/main/bin/activate

while true; do
  python scripts/write_stage_epoch_reports.py
  git add results/stage_expansion/epochs results/stage_expansion/EPOCHS.md
  if ! git diff --cached --quiet; then
    LAST_EPOCH="$(python -c "import json; print(json.load(open('results/stage_expansion/train_history.json'))[-1]['epoch'])")"
    git commit -m "Add stage expansion epoch ${LAST_EPOCH} report"
  fi
  git push origin main

  if [[ -f data/manifests/stage_expansion_pipeline/evaluation.complete ]]; then
    python scripts/write_stage_expansion_report.py
    git add results/stage_expansion checkpoints/stage_expansion scripts/write_stage_expansion_report.py
    if ! git diff --cached --quiet; then
      git commit -m "Add CIC-IDS2018 stage expansion results"
    fi
    git push origin main
    exit 0
  fi
  if ! supervisorctl status cybermind_stage_expansion | grep -q RUNNING; then
    echo "Expansion pipeline stopped before evaluation completed" >&2
    exit 1
  fi
  sleep 30
done
