#!/usr/bin/env python3
"""Audit option-(c) identity and CRF training-target coverage."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cybermind.models.stage_decoder import StageDecoder

EXCLUSION_KEYS = {
    "crf_transition_loss_excluded", "crf_transition_loss_exclusion_id",
    "crf_transition_loss_exclusion_pair", "crf_transition_loss_exclusion_rationale",
    "crf_transition_loss_exclusion_campaign",
    "crf_transition_loss_exclusion_campaign_interval_epoch",
    "crf_transition_loss_exclusion_source", "crf_transition_loss_exclusion_source_url",
    "crf_transition_loss_exclusion_source_file",
    "crf_transition_loss_exclusion_source_sha256",
    "crf_transition_loss_exclusion_reviewer_decision",
}


def equal_state(left, right) -> bool:
    scalar = ("node_ids", "timestamp", "y_infiltration", "y_stage", "scenario_id", "attack_label")
    return (all(getattr(left, key) == getattr(right, key) for key in scalar)
            and torch.equal(left.x, right.x)
            and torch.equal(left.edge_index, right.edge_index)
            and torch.equal(left.edge_attr, right.edge_attr))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="data/processed_real_chunk_r4_reviewed_resets")
    parser.add_argument("--derivative", default="data/processed_real_chunk_r4_option_c")
    parser.add_argument("--output", default="examples/real_data_validation/r4/option_c_audit.json")
    args = parser.parse_args()
    source, derivative = ROOT / args.source, ROOT / args.derivative
    decoder = StageDecoder()
    allowed = decoder.allowed_transitions
    reset_allowed = allowed | decoder.reset_transitions
    failures, reports = [], {}
    all_ids = set()
    for split in ("train", "val", "test"):
        before = torch.load(source / f"{split}.pt", map_location="cpu", weights_only=False)
        after = torch.load(derivative / f"{split}.pt", map_location="cpu", weights_only=False)
        if len(before) != len(after):
            failures.append(f"{split}: sample count changed")
            continue
        illegal = modeled_excluded = unhandled = unmodeled_first = excluded_legal = 0
        exclusion_state_occurrences = 0
        ids = set()
        for sample_index, (old_sample, new_sample) in enumerate(zip(before, after)):
            if (old_sample.scenario_id, old_sample.start_time, old_sample.window_seconds, len(old_sample.states),
                    old_sample.metadata) != (new_sample.scenario_id, new_sample.start_time,
                    new_sample.window_seconds, len(new_sample.states), new_sample.metadata):
                failures.append(f"{split}/{sample_index}: sample structure or metadata changed")
                continue
            for state_index, (old, new) in enumerate(zip(old_sample.states, new_sample.states)):
                if not equal_state(old, new):
                    failures.append(f"{split}/{sample_index}/{state_index}: tensor/target/state data changed")
                additions = set(new.metadata) - set(old.metadata)
                changed = {key for key in old.metadata if old.metadata[key] != new.metadata.get(key)}
                excluded = new.metadata.get("crf_transition_loss_excluded", False)
                if changed or not additions <= EXCLUSION_KEYS:
                    failures.append(f"{split}/{sample_index}/{state_index}: unauthorized metadata change")
                if excluded:
                    exclusion_state_occurrences += 1
                    ids.add(new.metadata.get("crf_transition_loss_exclusion_id"))
                    if additions != EXCLUSION_KEYS or new.metadata.get("campaign_reset", False):
                        failures.append(f"{split}/{sample_index}/{state_index}: incomplete or reset exclusion")
                elif additions:
                    failures.append(f"{split}/{sample_index}/{state_index}: provenance without exclusion")
            for destination_index, (left, right) in enumerate(zip(new_sample.states, new_sample.states[1:]), start=1):
                reset = right.metadata.get("campaign_reset", False)
                legal = bool((reset_allowed if reset else allowed)[left.y_stage, right.y_stage])
                excluded = right.metadata.get("crf_transition_loss_excluded", False)
                if not legal:
                    illegal += 1
                    if destination_index == 1:
                        unmodeled_first += 1
                    elif excluded:
                        modeled_excluded += 1
                    else:
                        unhandled += 1
                elif excluded and destination_index >= 2:
                    excluded_legal += 1
        all_ids |= ids
        reports[split] = {
            "samples": len(after), "unchanged_policy_illegal_occurrences": illegal,
            "modeled_illegal_occurrences_excluded_from_crf_loss": modeled_excluded,
            "illegal_occurrences_at_first_target_not_modeled_as_crf_edges": unmodeled_first,
            "unhandled_modeled_illegal_occurrences": unhandled,
            "modeled_legal_occurrences_excluded": excluded_legal,
            "exclusion_state_occurrences": exclusion_state_occurrences,
            "exclusion_boundary_ids": sorted(ids),
        }
    if len(all_ids) != 7:
        failures.append(f"expected seven unique boundary IDs, found {sorted(all_ids)}")
    if (source / "normalization.json").read_bytes() != (derivative / "normalization.json").read_bytes():
        failures.append("normalization changed")
    if reports.get("train", {}).get("unhandled_modeled_illegal_occurrences") != 0:
        failures.append("train retains unhandled modeled illegal CRF edges")
    if reports.get("train", {}).get("modeled_legal_occurrences_excluded") != 0:
        failures.append("option (c) excludes a legal modeled CRF edge")
    if any(reports.get(split, {}).get("exclusion_state_occurrences") for split in ("val", "test")):
        failures.append("validation/test contains option-(c) exclusions")
    report = {
        "passed": not failures, "source": args.source, "derivative": args.derivative,
        "scope": "CRF training loss only", "split_reports": reports,
        "unique_exclusion_boundary_ids": sorted(all_ids), "failures": failures,
        "viterbi_changed": False, "transition_policy_changed": False,
        "illegal_transition_metric_changed": False, "stage_targets_changed": False,
        "training_started": False,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 2)


if __name__ == "__main__":
    main()
