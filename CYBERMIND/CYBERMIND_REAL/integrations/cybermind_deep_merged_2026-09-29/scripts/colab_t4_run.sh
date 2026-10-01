#!/usr/bin/env bash
set -euo pipefail

# Run from the CYBERMIND repo root inside Google Colab.
# Example:
#   bash scripts/colab_t4_run.sh

export PYTHONUNBUFFERED=1
python -V
python -c 'import torch; print("PyTorch", torch.__version__, "CUDA", torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO GPU")'

python -m pip install -q -r requirements.txt
python scripts/gpu_preflight.py --config configs/colab_t4.yaml
python scripts/one_click_train.py --config configs/colab_t4.yaml
