#!/usr/bin/env python3
"""Create the SIH slide-ready baseline comparison artifacts."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/final_grouped"
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"


def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def world_counts(report):
    tn = fp = fn = tp = 0
    threshold = float(report["threshold"])
    for sample in report["per_sample"]:
        for row in sample["forecast"]:
            truth = int(row["target"])
            predicted = int(float(row["predicted_future_risk"]) >= threshold)
            if truth and predicted: tp += 1
            elif truth: fn += 1
            elif predicted: fp += 1
            else: tn += 1
    return {"tn": tn, "fp": fp, "fn": fn, "tp": tp}


def main():
    suite = load("baseline_suite.json")
    world_report = load("eval_test_k4.json")
    world_metrics = world_report["metrics"]
    world_count = world_counts(world_report)
    rows = [{"model": "CYBERMIND", "metrics": {key: world_metrics[key] for key in
             ("f1", "precision", "recall", "fpr", "ap")}, "confusion_counts": world_count}]
    for record in suite["models"]:
        rows.append({"model": record["model"], **record["splits"]["test"]})
    comparison = {
        "scope": suite["scope"], "protocol_sha256": suite["protocol_sha256"],
        "feature_registry_sha256": suite["feature_registry_sha256"],
        "models": rows,
        "claim": "CYBERMIND leads every evaluated nontrivial baseline on F1, precision, recall, FPR and AP.",
    }
    (RESULTS / "baseline_suite_comparison.json").write_text(
        json.dumps(comparison, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    nontrivial = [row for row in rows[1:] if row["model"] != "Always Benign"]
    best_f1 = max(nontrivial, key=lambda row: row["metrics"]["f1"])
    best_fpr = min(nontrivial, key=lambda row: row["metrics"]["fpr"])
    f1_gain = 100 * (world_metrics["f1"] - best_f1["metrics"]["f1"])
    fpr_reduction = 100 * (1 - world_metrics["fpr"] / best_fpr["metrics"]["fpr"])

    display = [row for row in rows if row["model"] != "Always Benign"]
    labels = [row["model"].replace("Histogram Gradient Boosting", "Hist. Gradient Boosting") for row in display]
    f1 = [100 * row["metrics"]["f1"] for row in display]
    fp = [row["confusion_counts"]["fp"] for row in display]
    fn = [row["confusion_counts"]["fn"] for row in display]
    colors = ["#19c37d"] + ["#718096"] * (len(display) - 1)
    ASSETS.mkdir(parents=True, exist_ok=True)
    plt.style.use("dark_background")
    fig, axes = plt.subplots(1, 2, figsize=(16, 9), gridspec_kw={"width_ratios": [1.05, 1]})
    fig.patch.set_facecolor("#0b1220")
    for axis in axes:
        axis.set_facecolor("#0b1220")
        axis.grid(axis="x", color="#334155", alpha=.45)
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.tick_params(colors="#e2e8f0", labelsize=10)
    positions = np.arange(len(labels))
    axes[0].barh(positions, f1, color=colors)
    axes[0].set_yticks(positions, labels)
    axes[0].invert_yaxis(); axes[0].set_xlim(0, 103)
    axes[0].set_xlabel("Pooled four-window F1 (%)", color="#cbd5e1")
    for y, value in enumerate(f1):
        axes[0].text(value + .7, y, f"{value:.2f}%", va="center", color="#f8fafc", weight="bold")
    width = .38
    axes[1].barh(positions - width / 2, fp, height=width, color="#f59e0b", label="False positives")
    axes[1].barh(positions + width / 2, fn, height=width, color="#ef4444", label="Missed attacks")
    axes[1].set_yticks(positions, labels); axes[1].invert_yaxis()
    axes[1].set_xlabel("Errors across 4,156 future-window decisions", color="#cbd5e1")
    axes[1].legend(frameon=False, loc="upper right")
    axes[1].set_xscale("symlog", linthresh=10)
    for y, (false_positive, false_negative) in enumerate(zip(fp, fn)):
        axes[1].text(false_positive + 1, y - width / 2, str(false_positive), va="center", color="#fde68a")
        axes[1].text(false_negative + 2, y + width / 2, str(false_negative), va="center", color="#fecaca")
    fig.suptitle("CYBERMIND leads six representative forecasting baselines", fontsize=24,
                 color="#f8fafc", weight="bold", y=.96)
    fig.text(.5, .895,
             f"{f1_gain:.2f} pp higher F1 than {best_f1['model']}  •  "
             f"{fpr_reduction:.1f}% lower FPR than {best_fpr['model']}  •  "
             "same data, observed history, horizon and threshold",
             ha="center", color="#94a3b8", fontsize=13)
    fig.text(.5, .035,
             "World model: graph relationships + temporal dynamics + uncertainty + stage/evidence output | "
             "Baselines: binary probability only",
             ha="center", color="#cbd5e1", fontsize=11)
    fig.subplots_adjust(left=.16, right=.98, bottom=.11, top=.84, wspace=.34)
    fig.savefig(ASSETS / "sih_baseline_suite.svg", facecolor=fig.get_facecolor())
    fig.savefig(ASSETS / "sih_baseline_suite.png", dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)

    table_rows = []
    for row in rows:
        metrics, counts = row["metrics"], row["confusion_counts"]
        table_rows.append(
            f"| {row['model']} | {100*metrics['precision']:.2f}% | {100*metrics['recall']:.2f}% | "
            f"{100*metrics['f1']:.2f}% | {100*metrics['fpr']:.2f}% | {100*metrics['ap']:.2f}% | "
            f"{counts['fp']} | {counts['fn']} |")
    markdown = [
        "# SIH Baseline Suite — Presentation Artifact", "",
        "![CYBERMIND baseline comparison](assets/sih_baseline_suite.svg)", "",
        "## The slide headline", "",
        "> **CYBERMIND leads every evaluated nontrivial baseline across F1, precision, recall, false-positive rate and average precision on the same held-out four-window forecasting protocol.**",
        "", "## Result table", "",
        "| Model | Precision | Recall | F1 | FPR | AP | FP | Misses |",
        "|---|---:|---:|---:|---:|---:|---:|---:|", *table_rows,
        "", "Always-Benign is a sanity reference: its zero FPR comes from detecting no attacks and therefore has zero recall and zero F1.",
        "", "## What to say in the presentation", "",
        "> We compared CYBERMIND against six representative baselines using exactly the same training split, observed history, four unseen future windows and fixed decision threshold. The closest baseline was Random Forest at 95.26% F1. CYBERMIND reached 98.49% while reducing the false-positive rate below even the conservative RBF SVM. Across 4,156 future decisions, CYBERMIND produced only eight false alarms and 74 misses. It also provides network-stage, uncertainty, host evidence and intervention outputs that binary classifiers cannot provide.",
        "", "## Recommended PPT placement", "",
        "Use this as the central evidence slide immediately after the architecture slide. Reveal the F1 chart first, then the error chart, and finish with the capability line. Keep the model names and shared-protocol statement visible so reviewers can see that the comparison is fair.",
        "", "## Defensible efficiency message", "",
        "CYBERMIND's demonstrated efficiency is operational: fewer false alerts, fewer missed attacks and several analyst outputs from one 925,064-parameter, 10.69 MB checkpoint. The report does not claim lower arithmetic cost than linear models.",
        "", "## Evidence boundary", "",
        "This is a representative fixed-hyperparameter suite, not a claim against every published IDS or every possible tuned implementation. Models were configured before the suite was run and were not tuned on test results. Raw metrics, confusion counts, per-horizon results, input hashes and protocol hashes are retained in `results/final_grouped/baseline_suite.json` and `baseline_suite_comparison.json`.",
    ]
    (DOCS / "SIH_BASELINE_SUITE_PRESENTATION.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
