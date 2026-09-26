#!/usr/bin/env python3
"""Write a compact, reviewable report for the expanded CIC-IDS2018 run."""
import json
from pathlib import Path
import torch

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/stage_expansion"


def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def metric(report, name):
    value = report["metrics"].get(name)
    return "n/a" if value is None else f"{value:.6f}"


def main():
    coverage = load("stage_coverage.json")
    val = load("eval_val_fixed.json")
    test = load("eval_test_fixed.json")
    status = load("status.json")
    checkpoint = ROOT / "checkpoints/stage_expansion/best.pt"
    lines = [
        "# CIC-IDS2018 stage-expansion training report",
        "",
        "The audited corpus was expanded with both corrected February 28 victim captures. "
        "The split remains chronological with a full-history purge at each boundary.",
        "",
        "## Coverage",
        "",
        "Target-window stage counts `[benign, recon, initial access, lateral movement, C2, exfiltration, unknown]`:",
        "",
    ]
    for split, values in coverage["target_occurrences"].items():
        lines.append(f"- **{split}:** `{values}`")
    lines += [
        "",
        "CIC-IDS2018 provides supported labels here for benign, reconnaissance, initial access, and C2. "
        "The added captures do not provide verified lateral-movement or exfiltration labels, so those stages remain unsupported rather than receiving inferred labels.",
        "",
        "## Fixed-threshold evaluation",
        "",
        "| Split | Precision | Recall | F1 | FPR |",
        "|---|---:|---:|---:|---:|",
        f"| Validation | {metric(val, 'precision')} | {metric(val, 'recall')} | {metric(val, 'f1')} | n/a (no benign targets) |",
        f"| Test | {metric(test, 'precision')} | {metric(test, 'recall')} | {metric(test, 'f1')} | {metric(test, 'fpr')} |",
        "",
        "## Artifact",
        "",
        f"- Selected epoch: `{torch.load(checkpoint, map_location='cpu', weights_only=False)['epoch']}`",
        f"- Checkpoint: `checkpoints/stage_expansion/best.pt` ({checkpoint.stat().st_size / 1_000_000:.2f} MB)",
        "- Selection used validation F1 with stage loss as a tie-breaker inside the configured F1 tolerance.",
        "",
        "## Interpretation",
        "",
        "Validation is an attack-only chronological segment because the Botnet Ares activity is continuous across that period. It supports early stopping on recall/F1 and stage loss but cannot estimate false positives. "
        "The final test contains both benign and C2 targets and supplies the fixed-threshold precision and false-positive measurement. "
        "The C2 holdout is later traffic from the same Botnet Ares campaign. It tests chronological generalization within that campaign; it does not establish generalization to unrelated C2 families. "
        "A defensible lateral-movement or exfiltration claim requires a separately labeled source with those stages and a source-isolated external test.",
        "",
    ]
    (RESULTS / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
