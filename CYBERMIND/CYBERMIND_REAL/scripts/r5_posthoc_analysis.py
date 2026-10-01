#!/usr/bin/env python3
"""R5 post-hoc host-correlate and validation-threshold analysis.

This script never trains the world model and never uses test labels to select a
threshold. It fits the already-defined feature-matched logistic baseline on the
training split, selects each operating threshold on validation, and applies it
once to test.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import argparse
import hashlib
import json
import sys

import numpy as np
import torch
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cybermind.baselines.logistic import LogisticBaseline
from cybermind.baselines.protocol import features, metric_report, sample_target, sha256
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.data.graph_builder import EDGE_FEATURE_NAMES, NODE_FEATURE_NAMES
from cybermind.data.real_chunk_label import BOT_VICTIMS
from cybermind.models.world_model import WorldModel
from cybermind.utils.config import edge_model_kwargs, stage_model_kwargs
from cybermind.utils.inference import verify_inference_states

SOURCE = "source: real-chunk validation, pre-Phase-5 — not full-corpus accuracy"


def select_threshold(targets, probabilities):
    """Maximize validation F1; break ties by lower FPR, then higher threshold."""
    y = np.asarray(targets, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    if len(y) == 0 or len(np.unique(y)) < 2:
        raise ValueError("Threshold calibration requires both classes on validation")
    candidates = sorted(set([0.0, 1.0, *p.tolist()]))
    scored = []
    for threshold in candidates:
        metrics, counts = metric_report(y, p, threshold)
        scored.append((float(metrics["f1"]), -float(metrics["fpr"]), float(threshold), metrics, counts))
    best = max(scored, key=lambda item: item[:3])
    return {
        "threshold": best[2],
        "validation_metrics": best[3],
        "validation_confusion_counts": best[4],
        "candidate_count": len(candidates),
        "selection_rule": "maximize validation F1; ties: lower validation FPR, then higher threshold",
    }


def load_model(checkpoint):
    ck = torch.load(checkpoint, map_location="cpu", weights_only=False)
    cfg = ck["config"]
    mc = cfg["model"]
    model = WorldModel(
        ck["node_dim"],
        **{key: mc[key] for key in (
            "graph_hidden", "graph_out", "temporal_dim", "nhead",
            "temporal_layers", "num_stages", "dropout")},
        graph_heads=mc.get("graph_heads", 8),
        **edge_model_kwargs(mc, mc),
        **stage_model_kwargs(cfg, cfg),
    )
    model.load_state_dict(ck["model_state"])
    model.eval()
    return ck, cfg, model


def world_probabilities(model, ck, cfg, dataset):
    result = []
    for sample in dataset:
        verify_inference_states(ck, sample.states)
        with torch.no_grad():
            forecast = model.forecast(
                sample.states[:-1], 1,
                n_rollouts=cfg["eval"].get("n_rollouts", 16),
                seed=cfg["eval"].get("rollout_seed", 0),
                explain=False,
            )
        result.append(float(forecast["infiltration_probability"][-1]))
    return np.asarray(result)


def feature_matched_probabilities(train, *evaluations):
    xtrain = np.stack([features(sample, "feature_matched") for sample in train])
    ytrain = np.asarray([sample_target(sample) for sample in train])
    if len(np.unique(ytrain)) < 2:
        prior = float(ytrain.mean())
        return [np.full(len(dataset), prior) for dataset in evaluations], "dummy_prior_single_class"
    model = LogisticBaseline().fit(xtrain, ytrain)
    outputs = []
    for dataset in evaluations:
        x = np.stack([features(sample, "feature_matched") for sample in dataset])
        outputs.append(model.predict_proba(x))
    return outputs, "logistic_regression"


def state_hosts(sample, observed):
    states = sample.states[:-1] if observed else [sample.states[-1]]
    return set().union(*(set(state.node_ids) for state in states))


def host_audit(train, test):
    test_targets = np.asarray([sample_target(sample) for sample in test])
    train_hosts = set().union(*(state_hosts(sample, False) for sample in train))
    positive = [sample for sample, y in zip(test, test_targets) if y == 1]
    negative = [sample for sample, y in zip(test, test_targets) if y == 0]
    target_positive_hosts = set().union(*(state_hosts(sample, False) for sample in positive))
    target_negative_hosts = set().union(*(state_hosts(sample, False) for sample in negative))
    observed_positive_hosts = set().union(*(state_hosts(sample, True) for sample in positive))
    observed_negative_hosts = set().union(*(state_hosts(sample, True) for sample in negative))

    def counts(samples, observed, host):
        return sum(host in state_hosts(sample, observed) for sample in samples)

    victims = []
    for host in sorted(BOT_VICTIMS, key=lambda value: tuple(map(int, value.split(".")))):
        victims.append({
            "host": host,
            "positive_target_windows": counts(positive, False, host),
            "negative_target_windows": counts(negative, False, host),
            "positive_observed_histories": counts(positive, True, host),
            "negative_observed_histories": counts(negative, True, host),
            "training_target_windows": counts(train, False, host),
            "present_in_training": host in train_hosts,
        })

    all_observed_hosts = observed_positive_hosts | observed_negative_hosts
    single_host = []
    for host in sorted(all_observed_hosts):
        pred = np.asarray([host in state_hosts(sample, True) for sample in test], dtype=int)
        correct_direct = bool(np.array_equal(pred, test_targets))
        correct_inverse = bool(np.array_equal(1 - pred, test_targets))
        if correct_direct or correct_inverse:
            single_host.append({"host": host, "direction": "present=>positive" if correct_direct else "absent=>positive"})

    signatures = defaultdict(set)
    signature_counts = Counter()
    for sample, target in zip(test, test_targets):
        signature = tuple(sorted(state_hosts(sample, True)))
        signatures[signature].add(int(target))
        signature_counts[signature] += 1
    conflicted_samples = sum(signature_counts[sig] for sig, labels in signatures.items() if len(labels) > 1)

    return {
        "test_target_counts": {"positive": int(test_targets.sum()), "negative": int((test_targets == 0).sum())},
        "victim_hosts": victims,
        "host_set_counts": {
            "positive_target_union": len(target_positive_hosts),
            "negative_target_union": len(target_negative_hosts),
            "target_union_overlap": len(target_positive_hosts & target_negative_hosts),
            "positive_observed_union": len(observed_positive_hosts),
            "negative_observed_union": len(observed_negative_hosts),
            "observed_union_overlap": len(observed_positive_hosts & observed_negative_hosts),
            "positive_target_hosts_seen_in_training": len(target_positive_hosts & train_hosts),
            "positive_target_hosts_not_seen_in_training": len(target_positive_hosts - train_hosts),
            "training_target_union": len(train_hosts),
        },
        "host_sets": {
            "positive_target": sorted(target_positive_hosts),
            "negative_target": sorted(target_negative_hosts),
            "target_overlap": sorted(target_positive_hosts & target_negative_hosts),
            "positive_observed": sorted(observed_positive_hosts),
            "negative_observed": sorted(observed_negative_hosts),
            "observed_overlap": sorted(observed_positive_hosts & observed_negative_hosts),
            "positive_target_not_in_training": sorted(target_positive_hosts - train_hosts),
        },
        "single_observed_host_perfect_classifiers": single_host,
        "observed_host_signatures": {
            "unique_signature_count": len(signatures),
            "label_conflicted_signature_count": sum(len(labels) > 1 for labels in signatures.values()),
            "samples_in_conflicted_signatures": conflicted_samples,
            "all_signatures_label_pure": all(len(labels) == 1 for labels in signatures.values()),
        },
    }


def _aggregate_column(sample, kind, index, reducer):
    arrays = []
    for state in sample.states[:-1]:
        tensor = state.x if kind == "node" else state.edge_attr
        if tensor.shape[0]:
            arrays.append(tensor[:, index].detach().cpu().numpy())
    values = np.concatenate(arrays) if arrays else np.asarray([0.0])
    return float(getattr(np, reducer)(values))


def single_feature_audit(dataset):
    targets = np.asarray([sample_target(sample) for sample in dataset])
    checks = []
    for kind, names in (("node", NODE_FEATURE_NAMES), ("edge", EDGE_FEATURE_NAMES)):
        for index, name in enumerate(names):
            for reducer in ("mean", "min", "max", "std"):
                values = np.asarray([_aggregate_column(sample, kind, index, reducer) for sample in dataset])
                if len(np.unique(values)) < 2:
                    auc = None
                else:
                    auc = float(roc_auc_score(targets, values))
                checks.append({"kind": kind, "feature": name, "history_aggregation": reducer, "roc_auc": auc})
    perfect = [row for row in checks if row["roc_auc"] is not None and (row["roc_auc"] <= 1e-12 or row["roc_auc"] >= 1 - 1e-12)]
    ranked = sorted((row for row in checks if row["roc_auc"] is not None),
                    key=lambda row: abs(row["roc_auc"] - 0.5), reverse=True)
    return {
        "construction": {
            "target": "int(states[-1].y_infiltration > 0)",
            "target_source": "any corrected non-BENIGN labeled flow in the unseen final window",
            "model_inputs": "numeric x, edge_index, edge_attr and observed timestamps from states[:-1]",
            "excluded_from_model_inputs": ["y_infiltration", "y_stage", "attack_label", "node_ids/IP strings", "corrected_rule_id", "label"],
            "direct_label_adjacent_input_found": False,
        },
        "empirical_test": {
            "scope": "each raw numeric node/edge column aggregated over observed history by mean/min/max/std",
            "checks": len(checks),
            "perfect_single_feature_checks": perfect,
            "top_10_by_distance_from_random_auc": ranked[:10],
        },
    }


def result_row(targets, probabilities, threshold):
    metrics, counts = metric_report(targets, probabilities, threshold)
    return {"threshold": float(threshold), "metrics": metrics, "confusion_counts": counts}


def write_markdown(report, path):
    host = report["host_identity_audit"]
    lines = [
        "# R5 post-hoc leakage and validation-threshold audit", "",
        f"**{SOURCE}.** This label applies to every result below.", "",
        "## Host-identity sanity check", "",
        (f"The held-out test split contains {host['test_target_counts']['positive']} positive and "
         f"{host['test_target_counts']['negative']} negative unseen target windows."), "",
        "| Botnet Ares victim | Positive targets | Negative targets | Positive histories | Negative histories | Training targets | Seen in train |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in host["victim_hosts"]:
        lines.append(f"| {row['host']} | {row['positive_target_windows']} | {row['negative_target_windows']} | "
                     f"{row['positive_observed_histories']} | {row['negative_observed_histories']} | "
                     f"{row['training_target_windows']} | {'yes' if row['present_in_training'] else 'no'} |")
    c = host["host_set_counts"]
    lines += ["", (f"Target-window host unions overlap on **{c['target_union_overlap']}** identities "
                    f"({c['positive_target_union']} positive-union hosts; {c['negative_target_union']} negative-union hosts). "
                    f"Observed-history unions overlap on **{c['observed_union_overlap']}** identities "
                    f"({c['positive_observed_union']} positive; {c['negative_observed_union']} negative)."), "",
              (f"No single observed-history host-presence indicator is a perfect classifier: **"
               f"{len(host['single_observed_host_perfect_classifiers'])}** found. Host-set signatures: "
               f"{host['observed_host_signatures']['unique_signature_count']} unique, "
               f"{host['observed_host_signatures']['label_conflicted_signature_count']} occur with both labels, covering "
               f"{host['observed_host_signatures']['samples_in_conflicted_signatures']} samples."), ""]
    lines += ["**Host-identity finding:** the ten declared Botnet Ares victim identities do not separate positive from negative windows; every victim occurs in both classes' observed histories and in training. Every test history has a unique complete host-set signature because external endpoints churn, so signature purity is vacuous and is not treated as evidence of host-based generalization.", ""]
    leak = report["single_feature_leakage_audit"]
    lines += ["## Target-construction and single-feature leakage", "",
              "`y_infiltration` is constructed from corrected labels in the unseen final window. The world model consumes only numeric behavior tensors and topology from `states[:-1]`; labels, targets, attack labels, rule IDs, and IP strings are not model inputs.", "",
              (f"The empirical audit tested {leak['empirical_test']['checks']} single-column/history-aggregation combinations. "
               f"Perfect single-feature separators found: **{len(leak['empirical_test']['perfect_single_feature_checks'])}**."), "",
              "| Strongest individual column | Tensor | History aggregation | Test ROC-AUC |",
              "|---|---|---|---:|"]
    for row in leak["empirical_test"]["top_10_by_distance_from_random_auc"][:5]:
        lines.append(f"| {row['feature']} | {row['kind']} | {row['history_aggregation']} | {row['roc_auc']:.9f} |")
    lines += ["", "**Leakage finding:** no target, stage, label, corrected-rule, attack-label, or IP-string field enters the model tensor, and no audited individual numeric column is an exact separator. However, mean node `scan_sequential_score` alone has test ROC-AUC 0.999891. The world model's AP/ROC-AUC of 1.0 is therefore a narrow correlate result on this three-day chunk, not evidence that the architecture learned general attack behavior or outperformed a simple behavioral signal.", "",
              "## Validation-only threshold calibration", "",
              f"Selection rule: {report['threshold_policy']['selection_rule']}. Test labels were not used. The 428-sequence validation split is extremely imbalanced: {report['threshold_policy']['validation_target_counts']['positive']} positive and {report['threshold_policy']['validation_target_counts']['negative']} negative targets.", "",
              "| Model / operating point | Threshold | TP | FP | TN | FN | F1 | FPR |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in report["comparison_rows"]:
        counts, metrics = row["confusion_counts"], row["metrics"]
        lines.append(f"| {row['label']} | {row['threshold']:.12g} | {counts['tp']} | {counts['fp']} | {counts['tn']} | {counts['fn']} | {metrics['f1']:.6f} | {metrics['fpr']:.6f} |")
    lines += ["", "The original 0.5 rows are retained. Calibrated thresholds were selected independently for each model on the 428-sequence validation split and then applied unchanged to the 431-sequence test split.", "",
              "At the validation-calibrated operating points, the world model has lower test F1 and higher test FPR than the feature-matched baseline. Both thresholds classify almost every test sample positive because validation contains only one negative example; these operating points are valid validation-only selections but weakly constrained for false-positive control.", "",
              "This post-hoc analysis does not retrain the world model, change checkpoint selection, or replace the R4 gate. R6 has not started.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    torch.set_num_threads(2)

    checkpoint = ROOT / args.checkpoint
    output = ROOT / args.output_dir
    if output.exists():
        raise FileExistsError("Use a new output directory to preserve prior evidence")
    ck, cfg, model = load_model(checkpoint)
    processed = ROOT / cfg["data"]["processed_dir"]
    train = GraphSequenceDataset(processed / "train.pt")
    val = GraphSequenceDataset(processed / "val.pt")
    test = GraphSequenceDataset(processed / "test.pt")
    yval = np.asarray([sample_target(sample) for sample in val])
    ytest = np.asarray([sample_target(sample) for sample in test])

    world_val = world_probabilities(model, ck, cfg, val)
    world_test = world_probabilities(model, ck, cfg, test)
    (base_val, base_test), baseline_kind = feature_matched_probabilities(train, val, test)
    world_selection = select_threshold(yval, world_val)
    baseline_selection = select_threshold(yval, base_val)

    rows = []
    for label, probabilities, threshold in (
        ("World model, fixed", world_test, 0.5),
        ("World model, validation-calibrated", world_test, world_selection["threshold"]),
        ("Feature-matched baseline, fixed", base_test, 0.5),
        ("Feature-matched baseline, validation-calibrated", base_test, baseline_selection["threshold"]),
    ):
        rows.append({"label": label, **result_row(ytest, probabilities, threshold)})

    report = {
        "source_qualifier": SOURCE,
        "analysis_kind": "post-hoc; no retraining and no test-label threshold selection",
        "input_hashes": {
            "checkpoint": sha256(checkpoint),
            "train": sha256(processed / "train.pt"),
            "val": sha256(processed / "val.pt"),
            "test": sha256(processed / "test.pt"),
            "normalization": sha256(processed / "normalization.json"),
        },
        "split_counts": {"train": len(train), "validation": len(val), "test": len(test)},
        "threshold_policy": {
            "selection_split": "validation only",
            "validation_target_counts": {"positive": int(yval.sum()), "negative": int((yval == 0).sum())},
            "selection_rule": world_selection["selection_rule"],
            "world_model": world_selection,
            "feature_matched_baseline": baseline_selection,
            "baseline_kind": baseline_kind,
        },
        "comparison_rows": rows,
        "probabilities": {
            "validation": {"targets": yval.tolist(), "world_model": world_val.tolist(), "feature_matched_baseline": base_val.tolist()},
            "test": {"targets": ytest.tolist(), "world_model": world_test.tolist(), "feature_matched_baseline": base_test.tolist()},
        },
        "host_identity_audit": host_audit(train, test),
        "single_feature_leakage_audit": single_feature_audit(test),
        "findings": {
            "host_identity": "Declared victim identities overlap positive and negative histories and training; victim identity does not separate the test labels.",
            "direct_target_leakage": "No label-adjacent field enters x, edge_index, or edge_attr; no audited individual numeric feature is an exact test separator.",
            "narrow_correlate": "Mean node scan_sequential_score alone reaches test ROC-AUC 0.9998908058528063, so world-model ROC-AUC 1.0 is narrow-correlate evidence, not evidence of a general architectural advantage.",
            "calibrated_comparison": "The world model has lower test F1 and higher test FPR than the feature-matched baseline at independently validation-calibrated thresholds.",
        },
        "limitations": [
            "Host and single-feature checks can identify direct or narrow correlates in this chunk; they cannot prove generalization.",
            "Validation threshold selection optimizes F1 on this selected real chunk and is not full-corpus calibration.",
            "Real-chunk validation does not include a Lateral Movement transition; kill-chain diversity is validated on real data for the other represented stages only.",
        ],
    }
    output.mkdir(parents=True)
    json_path = output / "posthoc_analysis.json"
    markdown_path = output / "posthoc_analysis.md"
    json_path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    write_markdown(report, markdown_path)
    manifest = {
        "posthoc_analysis.json": hashlib.sha256(json_path.read_bytes()).hexdigest(),
        "posthoc_analysis.md": hashlib.sha256(markdown_path.read_bytes()).hexdigest(),
    }
    (output / "sha256.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
