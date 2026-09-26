#!/bin/bash
set -euo pipefail
cd /workspace/cybermind/CYBERMIND_REAL
exec /usr/bin/unbuffer -p /venv/main/bin/python scripts/train.py \
  --config configs/cic2018_stage_expansion_improved.yaml --device cuda
