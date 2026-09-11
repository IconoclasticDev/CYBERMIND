#!/usr/bin/env bash
set -euo pipefail
python scripts/inspect_env.py
python scripts/make_synthetic.py
python scripts/train.py --config configs/smoke.yaml
python scripts/eval.py --config configs/smoke.yaml --checkpoint checkpoints/smoke.pt --split test
python scripts/visualize_rollout.py --config configs/smoke.yaml --checkpoint checkpoints/smoke.pt --split test
python scripts/counterfactual.py --config configs/smoke.yaml --checkpoint checkpoints/smoke.pt --split test --index 0
