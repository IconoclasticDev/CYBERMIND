#!/usr/bin/env python3
"""Single-model CYBERMIND one-command training entry point.

Usage:
    python scripts/one_click_train.py --config configs/colab_t4.yaml

The exact same model artifact can be trained on Colab T4, rented GPU, or 8 GB
laptops by changing only the config. No teacher/student split is used.
"""
from __future__ import annotations
import argparse, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/colab_t4.yaml")
    ap.add_argument("--epochs", type=int, default=0)
    ap.add_argument("--resume", default="")
    ap.add_argument("--no-download-cic2018", action="store_true")
    ap.add_argument("--skip-baseline", action="store_true")
    ap.add_argument("--skip-onnx", action="store_true")
    args = ap.parse_args()

    for rel in (
        "checkpoints", "export", "models", "results",
        "data/raw/CIC-IDS-2018", "data/intermediate", "data/processed"
    ):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)

    cmd = [PYTHON, str(ROOT / "scripts/launch_training.py"), "--config", args.config]
    if not args.no_download_cic2018:
        cmd.append("--download-cic2018")
    if args.epochs:
        cmd += ["--epochs", str(args.epochs)]
    if args.resume:
        cmd += ["--resume", args.resume]
    if args.skip_baseline:
        cmd.append("--skip-baseline")
    if args.skip_onnx:
        cmd.append("--skip-onnx")

    print("=" * 78)
    print("CYBERMIND — SINGLE MODEL ONE-CLICK RUN")
    print("Prepare → validate → baseline → train/resume → evaluate → export")
    print(f"Config: {args.config}")
    print("=" * 78, flush=True)
    return subprocess.run(cmd, cwd=ROOT, env={**os.environ, "PYTHONUNBUFFERED": "1"}).returncode


if __name__ == "__main__":
    raise SystemExit(main())
