#!/usr/bin/env python3
"""Verify the reviewed-reset derivative differs only in authorized metadata."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

RESET_KEYS = {
    "campaign_reset", "campaign_reset_boundary_id", "campaign_reset_campaign",
    "campaign_reset_campaign_end_utc", "campaign_reset_campaign_end_epoch",
    "campaign_reset_source", "campaign_reset_source_url",
    "campaign_reset_source_file", "campaign_reset_source_sha256",
    "campaign_reset_reviewer_decision",
}
AUTHORIZED = {
    1518624642.813819: "2018-02-14_ftp_bruteforce_end",
    1518636762.813819: "2018-02-14_ssh_bruteforce_end",
    1520020512.830365: "2018-03-02_botnet_ares_end",
}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def equal_state(left, right) -> bool:
    scalar = ("node_ids", "timestamp", "y_infiltration", "y_stage", "scenario_id", "attack_label")
    return (all(getattr(left, key) == getattr(right, key) for key in scalar)
            and torch.equal(left.x, right.x)
            and torch.equal(left.edge_index, right.edge_index)
            and torch.equal(left.edge_attr, right.edge_attr))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="data/processed_real_chunk_r2")
    parser.add_argument("--derivative", default="data/processed_real_chunk_r4_reviewed_resets")
    parser.add_argument("--output", default="examples/real_data_validation/r4/reset_derivative_identity_audit.json")
    args = parser.parse_args()
    source, derivative = ROOT / args.source, ROOT / args.derivative
    split_reports = {}
    failures = []
    for split in ("train", "val", "test"):
        before = torch.load(source / f"{split}.pt", map_location="cpu", weights_only=False)
        after = torch.load(derivative / f"{split}.pt", map_location="cpu", weights_only=False)
        if len(before) != len(after):
            failures.append(f"{split}: sample count changed")
            continue
        reset_occurrences = 0
        for sample_index, (old_sample, new_sample) in enumerate(zip(before, after)):
            if (old_sample.scenario_id, old_sample.start_time, old_sample.window_seconds, len(old_sample.states)) != (
                    new_sample.scenario_id, new_sample.start_time, new_sample.window_seconds, len(new_sample.states)):
                failures.append(f"{split}/{sample_index}: sample structure changed")
                continue
            if old_sample.metadata != new_sample.metadata:
                failures.append(f"{split}/{sample_index}: sample metadata changed")
            for state_index, (old, new) in enumerate(zip(old_sample.states, new_sample.states)):
                if not equal_state(old, new):
                    failures.append(f"{split}/{sample_index}/{state_index}: state data changed")
                old_meta = dict(old.metadata)
                new_meta = dict(new.metadata)
                additions = set(new_meta) - set(old_meta)
                changed_existing = {key for key in old_meta if old_meta[key] != new_meta.get(key)}
                if changed_existing or not additions <= RESET_KEYS:
                    failures.append(f"{split}/{sample_index}/{state_index}: unauthorized metadata change")
                reset = bool(new_meta.get("campaign_reset", False))
                reset_occurrences += int(reset)
                if reset:
                    timestamp = float(new_meta["window_start"])
                    matches = [identifier for expected, identifier in AUTHORIZED.items()
                               if abs(timestamp - expected) < 1e-6]
                    if (len(matches) != 1
                            or new_meta.get("campaign_reset_boundary_id") != matches[0]
                            or additions != RESET_KEYS):
                        failures.append(f"{split}/{sample_index}/{state_index}: invalid reset declaration")
                elif additions:
                    failures.append(f"{split}/{sample_index}/{state_index}: reset metadata without true reset")
        split_reports[split] = {
            "samples": len(after),
            "state_occurrences": sum(len(sample.states) for sample in after),
            "authorized_reset_state_occurrences": reset_occurrences,
        }
    if (source / "normalization.json").read_bytes() != (derivative / "normalization.json").read_bytes():
        failures.append("normalization.json changed")
    report = {
        "passed": not failures,
        "source": args.source,
        "derivative": args.derivative,
        "authorized_destination_windows": AUTHORIZED,
        "split_reports": split_reports,
        "normalization_sha256": digest(derivative / "normalization.json"),
        "failures": failures,
        "training_started": False,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 2)


if __name__ == "__main__":
    main()
