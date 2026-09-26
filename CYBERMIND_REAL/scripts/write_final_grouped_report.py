#!/usr/bin/env python3
"""Write compact human-readable reports for the final grouped training run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/final_grouped"
CHECKPOINTS = ROOT / "checkpoints/final_grouped"


def load_json(name: str):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def fmt(value):
    return "n/a" if value is None else f"{value:.6f}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    history = load_json("train_history.json")
    validation = load_json("eval_val_k4.json")
    test = load_json("eval_test_k4.json")
    audit = load_json("split_audit.json")
    best_path = CHECKPOINTS / "best.pt"
    last_path = CHECKPOINTS / "best_last.pt"
    checkpoint = torch.load(best_path, map_location="cpu", weights_only=False)
    best_epoch = int(checkpoint["epoch"])

    epoch_dir = RESULTS / "epochs"
    epoch_dir.mkdir(parents=True, exist_ok=True)
    for record in history:
        epoch = int(record["epoch"])
        train = record["train"]
        val = record["val"]
        body = [
            f"# Epoch {epoch}", "",
            f"- Training loss: {fmt(train.get('loss'))}",
            f"- Validation loss: {fmt(val.get('loss'))}",
            f"- Validation precision: {fmt(val.get('precision'))}",
            f"- Validation recall: {fmt(val.get('recall'))}",
            f"- Validation F1: {fmt(val.get('f1'))}",
            f"- Validation support: {val.get('positive')} attack / {val.get('negative')} benign target windows",
            f"- Selected as final best checkpoint: {'yes' if epoch == best_epoch else 'no'}",
            "",
            "The checkpoint policy uses validation F1 with stage loss as the tie-breaker inside the configured F1 tolerance.",
        ]
        (epoch_dir / f"epoch_{epoch:03d}.md").write_text("\n".join(body) + "\n", encoding="utf-8")

    vm = validation["metrics"]
    tm = test["metrics"]
    status = load_json("status.json")
    summary = [
        "# Final Grouped Training Report", "",
        "## Selection", "",
        f"- Best epoch: {best_epoch}",
        f"- Training termination: `{status['status']}` after epoch {status['last_completed_epoch']}",
        f"- Best checkpoint: `checkpoints/final_grouped/best.pt` ({best_path.stat().st_size / 1_000_000:.2f} MB)",
        f"- Best SHA-256: `{sha256(best_path)}`",
        f"- Final-state SHA-256: `{sha256(last_path)}`",
        "", "## Four-window evaluation", "",
        "| Split | Precision | Recall | F1 | FPR | AP | Stage macro-F1 |", 
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Validation | {fmt(vm.get('precision'))} | {fmt(vm.get('recall'))} | {fmt(vm.get('f1'))} | {fmt(vm.get('fpr'))} | {fmt(vm.get('average_precision'))} | {fmt(vm.get('stage_macro_f1'))} |",
        f"| Test | {fmt(tm.get('precision'))} | {fmt(tm.get('recall'))} | {fmt(tm.get('f1'))} | {fmt(tm.get('fpr'))} | {fmt(tm.get('average_precision'))} | {fmt(tm.get('stage_macro_f1'))} |",
        "", "## Data-integrity statement", "",
        f"- Mixed benign/attack validation: `{audit['mixed_terminal_classes']['val']}`",
        f"- Strict chronological capture groups: `{audit['strictly_chronological']}`",
        f"- Unseen stage-4 test gate: `{audit['gates']['unseen_stage_4_test']}`",
        f"- Comprehensive stage-training gate: `{audit['gates']['comprehensive_stage_training_ready']}`",
        "",
        "Stages 3 and 5 are absent from the available authoritative captures. This run is therefore a leakage-safe binary forecasting and unseen-stage-4 benchmark, not evidence of comprehensive seven-stage performance.",
    ]
    (RESULTS / "TRAINING_REPORT.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
