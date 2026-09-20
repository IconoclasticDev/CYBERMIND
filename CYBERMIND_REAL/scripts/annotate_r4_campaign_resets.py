#!/usr/bin/env python3
"""Create an R4 dataset derivative with only reviewer-authorized resets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Kept local so this metadata-only operation does not import pandas or execute
# any labeling code. The value must stay byte-for-byte identical to the pinned
# R1 label-source declaration.
CORRECTED_SOURCE = (
    "Distrinet CNS2022 corrected CSE-CIC-IDS2018 rules, "
    "commit f0ce502818e59e6cd062720ab2286c5ff6f2bdec"
)

RULE_PATH = ROOT / "data/real_chunk/rules/Distrinet_CICIDS2018_fixed_f0ce502.ipynb"
RULE_URL = ("https://github.com/GintsEngelen/CNS2022_Code/blob/"
            "f0ce502818e59e6cd062720ab2286c5ff6f2bdec/Labelling/"
            "CICIDS2018_labelling_fixed_CICFlowMeter.ipynb")
DECISION = "R4 reviewer decision — 2026-09-16"

# Exact temporal adjacencies observed in the frozen R2 derivative. A reset is
# declared at the destination state only. The seven March 1 in-campaign
# occupancy dropouts are deliberately absent.
BOUNDARIES = (
    {
        "id": "2018-02-14_ftp_bruteforce_end",
        "campaign": "FTP-BruteForce",
        "campaign_end_utc": "2018-02-14T16:10:31Z",
        "campaign_end_epoch": 1518624631.0,
        "source_window_start": 1518624612.813819,
        "destination_window_start": 1518624642.813819,
        "source_stage": 2,
        "destination_stage": 0,
    },
    {
        "id": "2018-02-14_ssh_bruteforce_end",
        "campaign": "SSH-BruteForce",
        "campaign_end_utc": "2018-02-14T19:32:30Z",
        "campaign_end_epoch": 1518636750.0,
        "source_window_start": 1518636732.813819,
        "destination_window_start": 1518636762.813819,
        "source_stage": 2,
        "destination_stage": 0,
    },
    {
        "id": "2018-03-02_botnet_ares_end",
        "campaign": "Botnet Ares",
        "campaign_end_utc": "2018-03-02T19:54:52Z",
        "campaign_end_epoch": 1520020492.0,
        "source_window_start": 1520020482.830365,
        "destination_window_start": 1520020512.830365,
        "source_stage": 4,
        "destination_stage": 0,
    },
)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def close(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) < 1e-6


def annotate(samples, split: str):
    transition_occurrences = {boundary["id"]: 0 for boundary in BOUNDARIES}
    destination_occurrences = {boundary["id"]: 0 for boundary in BOUNDARIES}
    seen_destinations = set()

    # Validate the exact reviewed source -> destination transitions first.
    for sample in samples:
        for source, destination in zip(sample.states, sample.states[1:]):
            for boundary in BOUNDARIES:
                if (close(source.metadata["window_start"], boundary["source_window_start"])
                        and close(destination.metadata["window_start"], boundary["destination_window_start"])):
                    if (source.y_stage, destination.y_stage) != (
                            boundary["source_stage"], boundary["destination_stage"]):
                        raise ValueError(f"{split}/{boundary['id']}: reviewed stage pair changed")
                    if not (source.metadata["window_start"] < boundary["campaign_end_epoch"]
                            <= destination.metadata["window_start"]):
                        raise ValueError(f"{split}/{boundary['id']}: campaign end is not between windows")
                    transition_occurrences[boundary["id"]] += 1

    # Annotate every occurrence of each reviewed destination state. Pickle may
    # preserve shared identities, so count occurrences separately from objects.
    for sample in samples:
        for state in sample.states:
            for boundary in BOUNDARIES:
                if close(state.metadata["window_start"], boundary["destination_window_start"]):
                    destination_occurrences[boundary["id"]] += 1
                    key = (id(state), boundary["id"])
                    if key in seen_destinations:
                        continue
                    seen_destinations.add(key)
                    if state.y_stage != boundary["destination_stage"]:
                        raise ValueError(f"{split}/{boundary['id']}: destination stage changed")
                    state.metadata.update({
                        "campaign_reset": True,
                        "campaign_reset_boundary_id": boundary["id"],
                        "campaign_reset_campaign": boundary["campaign"],
                        "campaign_reset_campaign_end_utc": boundary["campaign_end_utc"],
                        "campaign_reset_campaign_end_epoch": boundary["campaign_end_epoch"],
                        "campaign_reset_source": CORRECTED_SOURCE,
                        "campaign_reset_source_url": RULE_URL,
                        "campaign_reset_source_file": str(RULE_PATH.relative_to(ROOT)),
                        "campaign_reset_source_sha256": digest(RULE_PATH),
                        "campaign_reset_reviewer_decision": DECISION,
                    })

    # All non-reviewed states must remain explicitly or implicitly non-reset.
    authorized_destinations = {b["destination_window_start"] for b in BOUNDARIES}
    unauthorized = []
    for sample_index, sample in enumerate(samples):
        for state_index, state in enumerate(sample.states):
            if state.metadata.get("campaign_reset", False) and not any(
                    close(state.metadata["window_start"], expected)
                    for expected in authorized_destinations):
                unauthorized.append((sample_index, state_index, state.metadata["window_start"]))
    if unauthorized:
        raise ValueError(f"{split}: unauthorized campaign resets: {unauthorized[:3]}")
    return {
        "transition_occurrences": transition_occurrences,
        "destination_state_occurrences": destination_occurrences,
        "declared_boundary_ids": [key for key, count in transition_occurrences.items() if count],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed_real_chunk_r2")
    parser.add_argument("--output", default="data/processed_real_chunk_r4_reviewed_resets")
    parser.add_argument("--audit", default="examples/real_data_validation/r4/reset_annotation_audit.json")
    args = parser.parse_args()
    source, output = ROOT / args.input, ROOT / args.output
    audit_path = ROOT / args.audit
    if output.exists():
        raise FileExistsError(f"Preserve existing derivative: {output}")
    partial = output.with_name(output.name + ".partial")
    if partial.exists() or audit_path.exists():
        raise FileExistsError("Preserve existing partial/audit output")
    partial.mkdir(parents=True)
    reports = {}
    try:
        for name in ("normalization.json",):
            shutil.copy2(source / name, partial / name)
        for split in ("train", "val", "test"):
            samples = torch.load(source / f"{split}.pt", map_location="cpu", weights_only=False)
            reports[split] = annotate(samples, split)
            torch.save(samples, partial / f"{split}.pt")
        source_metadata = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
        source_metadata["campaign_reset_annotation"] = {
            "decision": DECISION,
            "rule_source": CORRECTED_SOURCE,
            "rule_url": RULE_URL,
            "rule_file": str(RULE_PATH.relative_to(ROOT)),
            "rule_file_sha256": digest(RULE_PATH),
            "authorized_boundaries": list(BOUNDARIES),
            "explicitly_untouched": "Seven March 1 in-campaign occupancy dropouts identified by the R4 failure audit.",
        }
        (partial / "metadata.json").write_text(json.dumps(source_metadata, indent=2) + "\n", encoding="utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        partial.replace(output)
        audit = {
            "status": "complete",
            "input": args.input,
            "output": args.output,
            "reviewer_decision": DECISION,
            "rule_source": CORRECTED_SOURCE,
            "rule_url": RULE_URL,
            "rule_file_sha256": digest(RULE_PATH),
            "authorized_boundaries": list(BOUNDARIES),
            "split_reports": reports,
            "output_sha256": {name: digest(output / name) for name in
                              ("train.pt", "val.pt", "test.pt", "normalization.json", "metadata.json")},
            "training_started": False,
        }
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(audit, indent=2))
    except Exception:
        if partial.exists():
            shutil.rmtree(partial)
        raise


if __name__ == "__main__":
    main()
