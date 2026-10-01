#!/usr/bin/env python3
"""Fail-closed audit for the R5 post-hoc evidence bundle."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.r5_posthoc_analysis import select_threshold


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--original-comparison", required=True)
    args = parser.parse_args()
    evidence = ROOT / args.evidence_dir
    original_path = ROOT / args.original_comparison
    report_path = evidence / "posthoc_analysis.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    original = json.loads(original_path.read_text(encoding="utf-8"))
    failures = []

    if report["split_counts"] != {"train": 1699, "validation": 428, "test": 431}:
        failures.append("split counts changed")
    if report["threshold_policy"]["selection_split"] != "validation only":
        failures.append("threshold selection split is not validation only")
    probabilities = report["probabilities"]
    for model_key in ("world_model", "feature_matched_baseline"):
        selected = select_threshold(probabilities["validation"]["targets"], probabilities["validation"][model_key])
        recorded = report["threshold_policy"][model_key]
        if selected["threshold"] != recorded["threshold"]:
            failures.append(f"{model_key} threshold does not reproduce from validation")
    if len(probabilities["test"]["targets"]) != 431:
        failures.append("test probability count changed")

    old_world = [row["predicted_future_risk"] for row in original["world_model"]["per_sample"]]
    old_base_row = next(row for row in original["baselines"]
                        if row["feature_registry"]["feature_mode"] == "feature_matched")
    old_base = [row["predicted_future_risk"] for row in old_base_row["per_sample"]]
    if old_world != probabilities["test"]["world_model"]:
        failures.append("world-model test probabilities differ from retained R5 evidence")
    if old_base != probabilities["test"]["feature_matched_baseline"]:
        failures.append("baseline test probabilities differ from retained R5 evidence")

    host = report["host_identity_audit"]
    if host["single_observed_host_perfect_classifiers"]:
        failures.append("a perfect single-host classifier exists")
    for victim in host["victim_hosts"]:
        if not (victim["positive_observed_histories"] and victim["negative_observed_histories"]
                and victim["present_in_training"]):
            failures.append(f"victim overlap claim failed for {victim['host']}")
    construction = report["single_feature_leakage_audit"]["construction"]
    if construction["direct_label_adjacent_input_found"]:
        failures.append("direct label-adjacent input was found")

    audit = {
        "passed": not failures,
        "failures": failures,
        "report_sha256": digest(report_path),
        "original_comparison_sha256": digest(original_path),
        "validation_thresholds_reproduced": not any("threshold" in failure for failure in failures),
        "original_test_probabilities_reproduced": not any("probabilities differ" in failure for failure in failures),
        "host_overlap_checked": True,
        "source_qualifier": report["source_qualifier"],
    }
    (evidence / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
