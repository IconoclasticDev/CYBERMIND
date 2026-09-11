#!/usr/bin/env python3
"""Single-command CYBERMIND lab launcher.

Run from the repository root:
    python scripts/one_click_train.py

It bootstraps output directories, downloads CIC-IDS2018 if needed, prepares the
corpus, validates leakage-safe splits, runs baselines, trains the teacher, evaluates
it, exports/verifies ONNX, and leaves artifacts in checkpoints/export/results.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def main() -> int:
    for rel in ("checkpoints", "export", "models", "results", "data/raw/CIC-IDS-2018",
                "data/intermediate", "data/processed_gb10"):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)

    cmd = [PYTHON, str(ROOT / "scripts/launch_training.py"),
           "--config", "configs/gb10_full.yaml", "--download-cic2018"]
    print("=" * 78)
    print("CYBERMIND ONE-CLICK LAB RUN")
    print("Download → prepare → validate → baseline → train → evaluate → ONNX")
    print("=" * 78, flush=True)
    p = subprocess.run(cmd, cwd=ROOT, env={**os.environ, "PYTHONUNBUFFERED": "1"})
    if p.returncode != 0:
        return p.returncode
    train_pt = ROOT / "data/processed_gb10/train.pt"
    if train_pt.exists():
        print("[ONE-CLICK] Teacher training complete; starting portable student distillation...", flush=True)
        distill = [PYTHON, str(ROOT / "scripts/distill_student.py"),
                   "--train-data", "data/processed_gb10/train.pt",
                   "--output", "models/cybermind_student_quant.onnx"]
        d = subprocess.run(distill, cwd=ROOT, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        if d.returncode != 0:
            print("[WARN] Teacher succeeded but student distillation failed. Re-run scripts/distill_student.py separately.", flush=True)
            return d.returncode
    else:
        print("[WARN] Training completed but data/processed_gb10/train.pt was not found; student distillation was skipped.", flush=True)
    print("[DONE] Teacher + portable student pipeline finished.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
