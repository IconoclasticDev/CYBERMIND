#!/usr/bin/env python3
"""Materialize one immutable Markdown and JSON report per completed epoch."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/stage_expansion"
REPORTS = RESULTS / "epochs"


def fmt(value):
    return "n/a" if value is None else f"{float(value):.6f}"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    history_path = RESULTS / "train_history.json"
    if not history_path.exists():
        return
    history = json.loads(history_path.read_text(encoding="utf-8"))
    REPORTS.mkdir(parents=True, exist_ok=True)
    table = [
        "# Stage-expansion epoch reports", "",
        "Validation is a later, attack-only Botnet Ares segment. Its precision is mechanically 1 when detections are positive and it cannot measure false positives; the final mixed test supplies that measurement.",
        "", "| Epoch | Train loss | Validation loss | Precision | Recall | F1 | Stage loss |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in history:
        epoch = int(record["epoch"])
        train, val = record["train"], record["val"]
        payload = json.dumps(record, indent=2) + "\n"
        atomic_write(REPORTS / f"epoch_{epoch:03d}.json", payload)
        markdown = [
            f"# Epoch {epoch}", "", "## Metrics", "",
            "| Metric | Training | Validation |", "|---|---:|---:|",
            f"| Total loss | {fmt(train.get('loss'))} | {fmt(val.get('loss'))} |",
            f"| Transition loss | {fmt(train.get('transition'))} | {fmt(val.get('transition'))} |",
            f"| Infiltration loss | {fmt(train.get('infiltration'))} | {fmt(val.get('infiltration'))} |",
            f"| Stage loss | {fmt(train.get('stage'))} | {fmt(val.get('stage'))} |",
            f"| Calibration loss | {fmt(train.get('calibration'))} | {fmt(val.get('calibration'))} |",
            f"| Graph consistency | {fmt(train.get('graph_consistency'))} | {fmt(val.get('graph_consistency'))} |",
            "", "## Detection on chronological validation", "",
            f"- Precision: `{fmt(val.get('precision'))}`",
            f"- Recall: `{fmt(val.get('recall'))}`",
            f"- F1: `{fmt(val.get('f1'))}`",
            f"- Positive targets: `{val.get('positive', 'n/a')}`",
            f"- Negative targets: `{val.get('negative', 'n/a')}`",
            f"- Threshold: `{val.get('threshold', 'n/a')}`",
            "",
            "This validation segment contains no benign targets. Use its recall/F1 and stage loss for training progress; use the final mixed test for precision and false-positive conclusions.",
            "",
        ]
        atomic_write(REPORTS / f"epoch_{epoch:03d}.md", "\n".join(markdown))
        table.append(
            f"| [{epoch}](epochs/epoch_{epoch:03d}.md) | {fmt(train.get('loss'))} | "
            f"{fmt(val.get('loss'))} | {fmt(val.get('precision'))} | "
            f"{fmt(val.get('recall'))} | {fmt(val.get('f1'))} | {fmt(val.get('stage'))} |"
        )
    atomic_write(RESULTS / "EPOCHS.md", "\n".join(table) + "\n")
    print(f"Wrote {len(history)} epoch reports", flush=True)


if __name__ == "__main__":
    main()
