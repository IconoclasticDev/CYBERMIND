#!/usr/bin/env python3
"""Audit the frozen R5 real-chunk Track A comparison."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPARISON = ROOT / "examples/real_data_validation/r5/attempt_2/comparison.json"
OUTPUT = ROOT / "examples/real_data_validation/r5/attempt_2/audit.json"
EXPECTED_SCOPE = "source: real-chunk validation, pre-Phase-5 — not full-corpus accuracy"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    report = json.loads(COMPARISON.read_text(encoding="utf-8"))
    failures = []
    if report.get("source_qualifier") != EXPECTED_SCOPE:
        failures.append("root source qualifier changed")
    if report.get("split") != "test" or report.get("threshold") != 0.5:
        failures.append("held-out split or fixed threshold changed")
    if report.get("forecast_horizon_windows") != 1 or not report.get("sample_alignment_verified"):
        failures.append("one-window aligned protocol not verified")
    rows = report.get("baselines", [])
    modes = [row["feature_registry"]["feature_mode"] for row in rows]
    if modes != ["node", "node_edge", "feature_matched"]:
        failures.append(f"baseline modes changed: {modes}")
    targets = [item["target"] for item in report["world_model"]["per_sample"]]
    if len(targets) != 431 or (targets.count(0), targets.count(1)) != (190, 241):
        failures.append("held-out targets changed")
    for row in rows:
        if row.get("source_qualifier") != EXPECTED_SCOPE:
            failures.append(f"{row['feature_registry']['feature_mode']}: source qualifier missing")
        if [item["target"] for item in row["per_sample"]] != targets:
            failures.append(f"{row['feature_registry']['feature_mode']}: targets misaligned")
        if len(row["per_sample"]) != 431:
            failures.append(f"{row['feature_registry']['feature_mode']}: probabilities incomplete")
    matched = rows[2]
    registry = matched["feature_registry"]
    if (registry["node_columns"], registry["edge_columns"], registry["graph_topology"]) != (34, 27, "summary statistics"):
        failures.append("feature-matched registry no longer covers node, edge and topology summaries")
    if report["world_model"]["checkpoint_sha256"] != "dd5da8fd76118e4b62b0747acc3631b486a404b1d12c15f9a9d79282477cc4aa":
        failures.append("checkpoint hash changed")
    verdict = report["model_vs_feature_matched"]
    if verdict["sentence"] != "The model loses to the feature-matched baseline on real data.":
        failures.append("plain verdict changed")
    fallback = report["single_class_fallback"]
    if fallback["invoked"] or fallback["training_target_counts"] != {"negative": 1143, "positive": 556}:
        failures.append("single-class fallback status changed")
    majority = report["trivial_majority_baseline"]
    if majority["confusion_counts"] != {"tn": 190, "fp": 0, "fn": 241, "tp": 0}:
        failures.append("always-Benign comparator changed")
    audit = {
        "passed": not failures,
        "source_qualifier": EXPECTED_SCOPE,
        "failures": failures,
        "comparison_sha256": digest(COMPARISON),
        "comparison_markdown_sha256": digest(COMPARISON.with_suffix(".md")),
        "checkpoint_sha256": report["world_model"]["checkpoint_sha256"],
        "train_sha256": rows[0]["source_sha256"]["train"],
        "test_sha256": rows[0]["source_sha256"]["test"],
        "normalization_sha256": registry["normalization_sha256"],
        "protocol_version": matched["protocol"]["version"],
        "protocol_sha256": matched["protocol_sha256"],
        "sample_probability_counts": {
            "node": len(rows[0]["per_sample"]),
            "node_edge": len(rows[1]["per_sample"]),
            "feature_matched": len(rows[2]["per_sample"]),
            "world_model": len(report["world_model"]["per_sample"]),
            "always_benign": len(majority["per_sample"]),
        },
        "verdict": verdict["sentence"],
    }
    OUTPUT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))
    raise SystemExit(0 if audit["passed"] else 2)


if __name__ == "__main__":
    main()
