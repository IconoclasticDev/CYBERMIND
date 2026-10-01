#!/usr/bin/env python3
"""Audit every observed stage transition before an expensive CRF training run."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cybermind.models.stage_decoder import StageDecoder


def utc(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", default="data/processed_real_chunk_r2")
    parser.add_argument("--output", default="examples/real_data_validation/r4/target_transition_audit.json")
    args = parser.parse_args()

    decoder = StageDecoder(num_stages=7)
    allowed = decoder.allowed_transitions
    reset_allowed = decoder.allowed_transitions | decoder.reset_transitions
    names = {
        0: "Benign", 1: "Reconnaissance", 2: "Initial Access",
        3: "Lateral Movement", 4: "Command & Control",
        5: "Exfiltration", 6: "Unknown/Ambiguous",
    }
    result = {
        "policy": "knowledge/stage_mapping.yaml",
        "rule": "An illegal transition is reported; labels never imply a reset.",
        "splits": {},
    }
    any_illegal = False
    processed = ROOT / args.processed
    for split in ("train", "val", "test"):
        samples = torch.load(processed / f"{split}.pt", map_location="cpu", weights_only=False)
        occurrence_pairs: Counter[str] = Counter()
        unique = {}
        explicit_resets = 0
        for sample_index, sample in enumerate(samples):
            for timestep, (source, destination) in enumerate(zip(sample.states, sample.states[1:]), start=1):
                reset = source.metadata.get("campaign_reset", False)
                # Reset applies at the destination timestep.
                reset = destination.metadata.get("campaign_reset", False)
                if not isinstance(reset, bool):
                    raise ValueError("campaign_reset must be an explicit boolean")
                explicit_resets += int(reset)
                legal = bool((reset_allowed if reset else allowed)[source.y_stage, destination.y_stage])
                if legal:
                    continue
                any_illegal = True
                pair = f"{names[source.y_stage]} -> {names[destination.y_stage]}"
                occurrence_pairs[pair] += 1
                key = (sample.scenario_id, source.metadata["window_start"], destination.metadata["window_start"])
                unique.setdefault(key, {
                    "scenario_id": sample.scenario_id,
                    "first_sample_index": sample_index,
                    "first_timestep": timestep,
                    "source_stage": source.y_stage,
                    "source_stage_name": names[source.y_stage],
                    "destination_stage": destination.y_stage,
                    "destination_stage_name": names[destination.y_stage],
                    "source_window_start_epoch": source.metadata["window_start"],
                    "source_window_start_utc": utc(source.metadata["window_start"]),
                    "destination_window_start_epoch": destination.metadata["window_start"],
                    "destination_window_start_utc": utc(destination.metadata["window_start"]),
                    "source_attack_label": source.attack_label,
                    "destination_attack_label": destination.attack_label,
                    "destination_campaign_reset": reset,
                })
        unique_pairs = Counter(
            f"{item['source_stage_name']} -> {item['destination_stage_name']}"
            for item in unique.values()
        )
        result["splits"][split] = {
            "samples": len(samples),
            "transition_occurrences": sum(len(sample.states) - 1 for sample in samples),
            "explicit_reset_occurrences": explicit_resets,
            "illegal_occurrences": sum(occurrence_pairs.values()),
            "illegal_occurrence_pairs": dict(sorted(occurrence_pairs.items())),
            "unique_illegal_boundaries": len(unique),
            "unique_illegal_pairs": dict(sorted(unique_pairs.items())),
            "boundaries": list(unique.values()),
        }
    result["passed"] = not any_illegal
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 2)


if __name__ == "__main__":
    main()
