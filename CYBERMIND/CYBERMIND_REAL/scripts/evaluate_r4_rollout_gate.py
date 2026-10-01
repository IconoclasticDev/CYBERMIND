#!/usr/bin/env python3
"""Evaluate the frozen four-step R4 gate on the held-out real-chunk split."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cybermind.data.dataset import GraphSequenceDataset
from cybermind.data.normalization import FeatureNormalizer
from cybermind.models.world_model import WorldModel
from cybermind.utils.config import edge_model_kwargs, stage_model_kwargs

LATERAL_DISCLOSURE = (
    "Real-chunk validation does not include a Lateral Movement transition. "
    "Kill-chain-diversity validation on real data covers the other represented stages only; "
    "it does not validate Lateral Movement."
)
FEATURE_DISCLOSURE = (
    "flow_feature_source: CYBERMIND custom directional packet exporter; 40-column schema; "
    "satisfies the project's 20-field packet-feature contract when verified, but is not "
    "CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter traffic-statistic "
    "columns. No CICFlowMeter feature parity is claimed."
)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build_model(checkpoint, device):
    cfg = checkpoint["config"]
    options = {key: cfg["model"][key] for key in (
        "graph_hidden", "graph_out", "temporal_dim", "nhead",
        "temporal_layers", "num_stages", "dropout")}
    options["graph_heads"] = cfg["model"].get("graph_heads", 8)
    model = WorldModel(checkpoint["node_dim"], **options,
                       **edge_model_kwargs(cfg["model"]),
                       **stage_model_kwargs(cfg)).to(device).eval()
    model.load_state_dict(checkpoint["model_state"])
    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--processed", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    checkpoint_path = ROOT / args.checkpoint
    processed = ROOT / args.processed
    output = ROOT / args.output
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite gate evidence: {output}")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    dataset = GraphSequenceDataset(processed / "test.pt")
    if not len(dataset):
        raise ValueError("Held-out test split is empty")
    prepared_normalization = FeatureNormalizer.load(processed / "normalization.json")
    checkpoint_normalization = FeatureNormalizer(checkpoint["normalization"])
    first = dataset[0].states[0]
    cfg = checkpoint["config"]
    contract = {
        "split": "test",
        "samples": len(dataset),
        "node_dim_match": checkpoint["node_dim"] == int(first.x.shape[1]),
        "edge_dim_match": cfg["model"]["edge_attr_dim"] == int(first.edge_attr.shape[1]),
        "history_match": cfg["data"]["history"] == len(dataset[0].states),
        "window_match": cfg["data"]["window_seconds"] == dataset[0].window_seconds,
        "normalization_match": checkpoint_normalization.fingerprint == prepared_normalization.fingerprint,
    }
    contract["passed"] = all(value for key, value in contract.items()
                             if key.endswith("_match"))
    if not contract["passed"]:
        raise ValueError(f"Checkpoint/test preprocessing mismatch: {contract}")
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    model = build_model(checkpoint, device)
    steps = int(cfg["eval"]["rollout_steps"])
    rollouts = int(cfg["eval"].get("n_rollouts", 4))
    seed = int(cfg["eval"].get("rollout_seed", 0))
    histograms = [Counter() for _ in range(steps)]
    illegal = [0] * steps
    allowed = model.stage_decoder.allowed_transitions
    with torch.no_grad():
        for sample in dataset:
            observed = [replace(state, x=state.x.to(device),
                                edge_index=state.edge_index.to(device),
                                edge_attr=state.edge_attr.to(device))
                        for state in sample.states[:-1]]
            result = model.forecast(observed, k=steps, n_rollouts=rollouts,
                                    seed=seed, explain=False)
            decoded = result["decoded_stages"]
            for index in range(steps):
                source, destination = int(decoded[index]), int(decoded[index + 1])
                histograms[index][destination] += 1
                illegal[index] += int(not bool(allowed[source, destination]))
    per_step = []
    for index, histogram in enumerate(histograms, start=1):
        distinct = len(set(histogram) - {6})
        unknown = histogram.get(6, 0)
        passed = distinct >= 2 and unknown < len(dataset) and illegal[index - 1] == 0
        per_step.append({
            "step": index,
            "samples": len(dataset),
            "decoded_histogram": {str(key): value for key, value in sorted(histogram.items())},
            "distinct_non_unknown": distinct,
            "unknown_count": unknown,
            "illegal_count": illegal[index - 1],
            "passed": passed,
        })
    report = {
        "gate": "R4 held-out real-chunk four-step rollout",
        "passed": all(item["passed"] for item in per_step),
        "requirements": {
            "minimum_distinct_non_unknown_per_step": 2,
            "maximum_illegal_transitions_per_step": 0,
            "unknown_count_must_be_below_sample_count": True,
        },
        "checkpoint": args.checkpoint,
        "checkpoint_sha256": digest(checkpoint_path),
        "selected_epoch": checkpoint["epoch"],
        "selection_state": checkpoint["selection_state"],
        "processed": args.processed,
        "test_sha256": digest(processed / "test.pt"),
        "device": str(device),
        "rollout_steps": steps,
        "n_rollouts": rollouts,
        "seed": seed,
        "preprocessing_contract": contract,
        "per_step": per_step,
        "lateral_movement_disclosure": LATERAL_DISCLOSURE,
        "fallback_feature_disclosure": FEATURE_DISCLOSURE,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 2)


if __name__ == "__main__":
    main()
