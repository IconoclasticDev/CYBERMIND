#!/usr/bin/env python3
"""Build the frozen, same-split world-model versus logistic comparison."""
from __future__ import annotations

import json
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/final_grouped"


def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def world_counts(report):
    threshold = float(report["threshold"])
    tn = fp = fn = tp = 0
    for sample in report["per_sample"]:
        for row in sample["forecast"]:
            truth = int(row["target"])
            prediction = int(float(row["predicted_future_risk"]) >= threshold)
            if truth == 1 and prediction == 1:
                tp += 1
            elif truth == 1:
                fn += 1
            elif prediction == 1:
                fp += 1
            else:
                tn += 1
    return {"tn": tn, "fp": fp, "fn": fn, "tp": tp}


def percent(value):
    return f"{100 * value:.2f}%"


def main():
    checkpoint_path = ROOT / "checkpoints/final_grouped/best.pt"
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    parameters = sum(value.numel() for value in checkpoint["model_state"].values())
    comparisons = {}
    for split in ("val", "test"):
        world = load(f"eval_{split}_k4.json")
        baseline = load(f"baseline_{split}_k4.json")
        wm, bm = world["metrics"], baseline["metrics"]
        wc = world_counts(world)
        bc = baseline["confusion_counts"]
        comparisons[split] = {
            "world_model": {"metrics": {key: wm[key] for key in ("f1", "precision", "recall", "fpr", "ap")},
                            "confusion_counts": wc},
            "feature_matched_logistic": {"metrics": {key: bm[key] for key in ("f1", "precision", "recall", "fpr", "ap")},
                                         "confusion_counts": bc},
            "absolute_metric_difference": {key: wm[key] - bm[key] for key in ("f1", "precision", "recall", "fpr", "ap")},
        }
    test = comparisons["test"]
    wc = test["world_model"]["confusion_counts"]
    bc = test["feature_matched_logistic"]["confusion_counts"]
    fpr_ratio = test["feature_matched_logistic"]["metrics"]["fpr"] / test["world_model"]["metrics"]["fpr"]
    false_alarm_reduction = 1 - wc["fp"] / bc["fp"]
    comparisons["summary"] = {
        "same_protocol": True,
        "future_window_decisions": sum(wc.values()),
        "f1_gain_percentage_points": 100 * test["absolute_metric_difference"]["f1"],
        "false_positives_avoided": bc["fp"] - wc["fp"],
        "missed_attacks_avoided": bc["fn"] - wc["fn"],
        "relative_false_alarm_reduction": false_alarm_reduction,
        "fpr_reduction_factor": fpr_ratio,
        "world_model_parameters": parameters,
        "world_model_checkpoint_mb": checkpoint_path.stat().st_size / 1_000_000,
        "logistic_coefficients": 4 * (int(load("baseline_test_k4.json")["feature_registry"]["flattened_width"]) + 1),
        "efficiency_interpretation": "Operational alert efficiency, not compute-speed superiority.",
    }
    (RESULTS / "model_comparison.json").write_text(
        json.dumps(comparisons, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    wm = test["world_model"]["metrics"]
    bm = test["feature_matched_logistic"]["metrics"]
    summary = comparisons["summary"]
    lines = [
        "# CYBERMIND vs Feature-Matched Logistic Baseline", "",
        "Both systems receive the same four observed graph windows, training split, held-out capture-day test split, fixed threshold `0.5`, and four unseen target windows. The baseline receives all node and edge columns with the registered graph-summary aggregations; it never reads future features.",
        "", "## Held-out four-window result", "",
        "| Model | Precision | Recall | F1 | FPR | AP | False positives | Misses |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| CYBERMIND world model | {percent(wm['precision'])} | {percent(wm['recall'])} | {percent(wm['f1'])} | {percent(wm['fpr'])} | {percent(wm['ap'])} | {wc['fp']} | {wc['fn']} |",
        f"| Feature-matched logistic | {percent(bm['precision'])} | {percent(bm['recall'])} | {percent(bm['f1'])} | {percent(bm['fpr'])} | {percent(bm['ap'])} | {bc['fp']} | {bc['fn']} |",
        "", "## Judge-facing measured advantages", "",
        f"- **{summary['f1_gain_percentage_points']:.2f} percentage-point F1 gain.**",
        f"- **{100 * summary['relative_false_alarm_reduction']:.1f}% fewer false alarms:** {wc['fp']} instead of {bc['fp']} across {summary['future_window_decisions']:,} future-window decisions.",
        f"- **{summary['fpr_reduction_factor']:.1f}× lower false-positive rate:** {percent(wm['fpr'])} instead of {percent(bm['fpr'])}.",
        f"- **{summary['missed_attacks_avoided']} fewer missed attack windows:** {wc['fn']} instead of {bc['fn']}.",
        f"- Compact teacher: **{parameters:,} parameters** and **{summary['world_model_checkpoint_mb']:.2f} MB**, including training state.",
        "", "## Capability difference", "",
        "Logistic regression provides one binary probability per horizon. CYBERMIND additionally models graph relationships and temporal state transitions, generates stochastic future trajectories, estimates rollout dispersion, decodes stage progression, exposes host/edge evidence, and supports intervention sensitivity probes.",
        "", "## Efficiency wording", "",
        "The measured efficiency advantage is operational: dramatically fewer false alerts for analysts while producing several decision outputs in one compact model. Logistic regression is computationally simpler, so this report does not claim CYBERMIND has lower arithmetic cost or latency without a separate controlled benchmark.",
    ]
    (ROOT / "docs/SIH_BASELINE_COMPARISON.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
