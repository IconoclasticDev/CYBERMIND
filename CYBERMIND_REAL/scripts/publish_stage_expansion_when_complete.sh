#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source /venv/main/bin/activate

while [[ ! -f data/manifests/stage_expansion_pipeline/evaluation.complete ]]; do
  if ! supervisorctl status cybermind_stage_expansion | grep -q RUNNING; then
    echo "Expansion pipeline stopped before evaluation completed" >&2
    exit 1
  fi
  sleep 60
done

python scripts/write_stage_expansion_report.py
git add results/stage_expansion checkpoints/stage_expansion scripts/write_stage_expansion_report.py
if ! git diff --cached --quiet; then
  git commit -m "Add CIC-IDS2018 stage expansion results"
  git push origin main
fi
