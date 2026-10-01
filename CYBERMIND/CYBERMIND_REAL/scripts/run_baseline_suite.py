#!/usr/bin/env python3
"""Run representative binary forecasting baselines on the frozen K-step protocol."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cybermind.baselines.protocol import (PROTOCOL, features, metric_report,
                                          record_hash, sample_targets, sha256)
from cybermind.data.dataset import GraphSequenceDataset


PROCESSED = ROOT / "data/processed_final_grouped"
OUTPUT = ROOT / "results/final_grouped/baseline_suite.json"
HORIZON = 4
THRESHOLD = 0.5
SEED = 42


def factories():
    return {
        "Logistic Regression": lambda: make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)),
        "Linear SGD": lambda: make_pipeline(
            StandardScaler(), SGDClassifier(loss="log_loss", max_iter=2000, tol=1e-4,
                                             class_weight="balanced", random_state=SEED)),
        "RBF SVM": lambda: make_pipeline(
            StandardScaler(), SVC(C=1.0, kernel="rbf", probability=True,
                                  class_weight="balanced", random_state=SEED, cache_size=4000)),
        "Random Forest": lambda: RandomForestClassifier(
            n_estimators=250, max_depth=16, min_samples_leaf=2,
            class_weight="balanced_subsample", n_jobs=-1, random_state=SEED),
        "Histogram Gradient Boosting": lambda: HistGradientBoostingClassifier(
            max_iter=150, learning_rate=0.05, max_depth=8, l2_regularization=0.1,
            class_weight="balanced", random_state=SEED),
        "MLP": lambda: make_pipeline(
            StandardScaler(), MLPClassifier(hidden_layer_sizes=(128,), activation="relu",
                                             batch_size=64, learning_rate_init=1e-3,
                                             max_iter=150, early_stopping=True,
                                             n_iter_no_change=12, random_state=SEED)),
    }


def main():
    np.random.seed(SEED)
    datasets = {name: GraphSequenceDataset(PROCESSED / f"{name}.pt")
                for name in ("train", "val", "test")}
    matrices = {
        name: np.stack([features(sample, "feature_matched", holdout=HORIZON)
                        for sample in dataset])
        for name, dataset in datasets.items()
    }
    targets = {
        name: np.asarray([sample_targets(sample, HORIZON) for sample in dataset], dtype=int)
        for name, dataset in datasets.items()
    }
    if len({matrix.shape[1] for matrix in matrices.values()}) != 1:
        raise ValueError("Feature widths differ across frozen splits")

    results = []
    for model_name in ("Always Benign", *factories().keys()):
        probabilities = {"val": [], "test": []}
        per_horizon = {"val": [], "test": []}
        training_seconds = 0.0
        prediction_seconds = {"val": 0.0, "test": 0.0}
        for step in range(HORIZON):
            ytrain = targets["train"][:, step]
            if model_name == "Always Benign":
                for split in ("val", "test"):
                    probabilities[split].append(np.zeros(len(datasets[split]), dtype=float))
                continue
            estimator = factories()[model_name]()
            started = time.perf_counter()
            estimator.fit(matrices["train"], ytrain)
            training_seconds += time.perf_counter() - started
            for split in ("val", "test"):
                started = time.perf_counter()
                values = estimator.predict_proba(matrices[split])[:, 1]
                prediction_seconds[split] += time.perf_counter() - started
                probabilities[split].append(values)

        split_results = {}
        for split in ("val", "test"):
            matrix = np.stack(probabilities[split], axis=1)
            metrics, counts = metric_report(targets[split].ravel(), matrix.ravel(), THRESHOLD)
            for step in range(HORIZON):
                step_metrics, step_counts = metric_report(
                    targets[split][:, step], matrix[:, step], THRESHOLD)
                per_horizon[split].append({"step": step + 1, "metrics": step_metrics,
                                           "confusion_counts": step_counts})
            split_results[split] = {
                "metrics": metrics, "confusion_counts": counts,
                "per_horizon": per_horizon[split],
                "prediction_seconds": prediction_seconds[split],
                "prediction_ms_per_sequence": 1000 * prediction_seconds[split] / len(datasets[split]),
            }
        results.append({"model": model_name, "training_seconds": training_seconds,
                        "splits": split_results})

    registry = {
        "feature_mode": "feature_matched", "flattened_width": int(matrices["train"].shape[1]),
        "observed_windows": len(datasets["train"][0].states) - HORIZON,
        "forecast_horizon_windows": HORIZON,
        "models": list(("Always Benign", *factories().keys())),
        "fixed_hyperparameters": True, "seed": SEED,
    }
    report = {
        "scope": "Representative fixed-hyperparameter baseline suite; not every published IDS model.",
        "protocol": PROTOCOL, "protocol_sha256": record_hash(PROTOCOL),
        "feature_registry": registry, "feature_registry_sha256": record_hash(registry),
        "threshold": THRESHOLD,
        "source_sha256": {name: sha256(PROCESSED / f"{name}.pt") for name in datasets},
        "split_counts": {name: len(dataset) for name, dataset in datasets.items()},
        "models": results,
        "timing_note": "Indicative wall time on this host; not a controlled cross-hardware latency claim.",
    }
    OUTPUT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({row["model"]: row["splits"]["test"]["metrics"] for row in results}, indent=2))


if __name__ == "__main__":
    main()
