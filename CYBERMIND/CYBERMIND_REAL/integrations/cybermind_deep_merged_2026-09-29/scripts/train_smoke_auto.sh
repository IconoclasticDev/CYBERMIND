#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python scripts/make_synthetic.py --output data/processed/smoke.pt --num-sequences 64
python scripts/smoke_all.sh
