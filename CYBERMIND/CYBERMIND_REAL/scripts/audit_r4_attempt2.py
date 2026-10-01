#!/usr/bin/env python3
"""Freeze hashes and invariants for the authorized R4 second attempt."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_DIR = ROOT / "checkpoints/real_chunk_r4/attempt_2"
RESULT_DIR = ROOT / "results/real_chunk_r4/attempt_2"
GATE_PATH = ROOT / "examples/real_data_validation/r4/attempt_2/rollout_gate.json"
OUTPUT = ROOT / "examples/real_data_validation/r4/attempt_2/artifact_manifest.json"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def entry(path: Path) -> dict:
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "bytes": path.stat().st_size, "sha256": digest(path)}


def main():
    status = json.loads((RESULT_DIR / "status.json").read_text(encoding="utf-8"))
    history = json.loads((RESULT_DIR / "train_history.json").read_text(encoding="utf-8"))
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    selected = torch.load(CHECKPOINT_DIR / "best.pt", map_location="cpu", weights_only=False)
    epoch_paths = sorted((CHECKPOINT_DIR / "epochs").glob("epoch_*.pt"))
    epochs = [torch.load(path, map_location="cpu", weights_only=False)["epoch"] for path in epoch_paths]
    failures = []
    if status.get("status") != "stopped_on_first_collapse" or status.get("last_completed_epoch") != 21:
        failures.append("run did not persist the expected first-collapse stop at epoch 21")
    if len(history) != 21 or [row["epoch"] for row in history] != list(range(1, 22)):
        failures.append("history is not a complete ordered 21-epoch record")
    if epochs != list(range(1, 22)):
        failures.append("per-epoch checkpoints are incomplete")
    if selected.get("epoch") != 1 or selected.get("selection_state", {}).get("selected_epoch") != 1:
        failures.append("validation-selected checkpoint is not epoch 1")
    if not gate.get("passed") or gate.get("selected_epoch") != 1:
        failures.append("held-out gate did not pass on selected epoch 1")
    if gate.get("checkpoint_sha256") != digest(CHECKPOINT_DIR / "best.pt"):
        failures.append("gate checkpoint hash does not match selected checkpoint")
    artifacts = [ROOT / "configs/real_chunk_r4_attempt2.yaml", GATE_PATH]
    artifacts += sorted(path for path in RESULT_DIR.iterdir() if path.is_file())
    artifacts += [CHECKPOINT_DIR / "best.pt", CHECKPOINT_DIR / "best_last.pt"] + epoch_paths
    report = {
        "passed": not failures,
        "run_status": status["status"],
        "last_completed_epoch": status["last_completed_epoch"],
        "selected_epoch": selected["epoch"],
        "heldout_gate_passed": gate["passed"],
        "epoch_checkpoints_preserved": len(epoch_paths),
        "failures": failures,
        "artifacts": [entry(path) for path in artifacts],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "artifacts"}, indent=2))
    raise SystemExit(0 if report["passed"] else 2)


if __name__ == "__main__":
    main()
