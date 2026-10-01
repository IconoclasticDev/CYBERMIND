#!/usr/bin/env python3
"""Create the reviewer-authorized R4 option-(c) training derivative."""
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

RULE_FILE = ROOT / "data/real_chunk/rules/Distrinet_CICIDS2018_fixed_f0ce502.ipynb"
RULE_COMMIT = "f0ce502818e59e6cd062720ab2286c5ff6f2bdec"
RULE_URL = ("https://github.com/GintsEngelen/CNS2022_Code/blob/"
            f"{RULE_COMMIT}/Labelling/CICIDS2018_labelling_fixed_CICFlowMeter.ipynb")
DECISION = "R4 reviewer decision — option (c) authorized — 2026-09-20"

BOUNDARIES = (
    {"id": "mar1_dropbox_135342", "pair": "Initial Access -> Benign",
     "source_stage": 2, "destination_stage": 0,
     "source_window_start": 1519912392.813819, "destination_window_start": 1519912422.813819,
     "source_window_utc": "2018-03-01T13:53:12.813819Z", "destination_window_utc": "2018-03-01T13:53:42.813819Z",
     "campaign": "Infiltration - Dropbox Download", "campaign_start_epoch": 1519912390.0,
     "campaign_end_epoch": 1519912760.0, "boundary_relation": "both window starts are inside the active interval"},
    {"id": "mar1_dropbox_135742", "pair": "Initial Access -> Benign",
     "source_stage": 2, "destination_stage": 0,
     "source_window_start": 1519912632.813819, "destination_window_start": 1519912662.813819,
     "source_window_utc": "2018-03-01T13:57:12.813819Z", "destination_window_utc": "2018-03-01T13:57:42.813819Z",
     "campaign": "Infiltration - Dropbox Download", "campaign_start_epoch": 1519912390.0,
     "campaign_end_epoch": 1519912760.0, "boundary_relation": "both window starts are inside the active interval"},
    {"id": "mar1_nmap_142012", "pair": "Reconnaissance -> Benign",
     "source_stage": 1, "destination_stage": 0,
     "source_window_start": 1519913982.813819, "destination_window_start": 1519914012.813819,
     "source_window_utc": "2018-03-01T14:19:42.813819Z", "destination_window_utc": "2018-03-01T14:20:12.813819Z",
     "campaign": "Infiltration - NMAP Portscan", "campaign_start_epoch": 1519913388.354333,
     "campaign_end_epoch": 1519933092.182726, "boundary_relation": "both window starts are inside the active interval"},
    {"id": "mar1_nmap_143012", "pair": "Reconnaissance -> Benign",
     "source_stage": 1, "destination_stage": 0,
     "source_window_start": 1519914582.813819, "destination_window_start": 1519914612.813819,
     "source_window_utc": "2018-03-01T14:29:42.813819Z", "destination_window_utc": "2018-03-01T14:30:12.813819Z",
     "campaign": "Infiltration - NMAP Portscan", "campaign_start_epoch": 1519913388.354333,
     "campaign_end_epoch": 1519933092.182726, "boundary_relation": "both window starts are inside the active interval"},
    {"id": "mar1_nmap_145642", "pair": "Reconnaissance -> Benign",
     "source_stage": 1, "destination_stage": 0,
     "source_window_start": 1519916172.813819, "destination_window_start": 1519916202.813819,
     "source_window_utc": "2018-03-01T14:56:12.813819Z", "destination_window_utc": "2018-03-01T14:56:42.813819Z",
     "campaign": "Infiltration - NMAP Portscan", "campaign_start_epoch": 1519913388.354333,
     "campaign_end_epoch": 1519933092.182726, "boundary_relation": "both window starts are inside the active interval"},
    {"id": "mar1_nmap_184712", "pair": "Reconnaissance -> Benign",
     "source_stage": 1, "destination_stage": 0,
     "source_window_start": 1519930002.813819, "destination_window_start": 1519930032.813819,
     "source_window_utc": "2018-03-01T18:46:42.813819Z", "destination_window_utc": "2018-03-01T18:47:12.813819Z",
     "campaign": "Infiltration - NMAP Portscan", "campaign_start_epoch": 1519913388.354333,
     "campaign_end_epoch": 1519933092.182726, "boundary_relation": "both window starts are inside the active interval"},
    {"id": "mar1_nmap_193812", "pair": "Reconnaissance -> Benign",
     "source_stage": 1, "destination_stage": 0,
     "source_window_start": 1519933062.813819, "destination_window_start": 1519933092.813819,
     "source_window_utc": "2018-03-01T19:37:42.813819Z", "destination_window_utc": "2018-03-01T19:38:12.813819Z",
     "campaign": "Infiltration - NMAP Portscan", "campaign_start_epoch": 1519913388.354333,
     "campaign_end_epoch": 1519933092.182726,
     "boundary_relation": "source window overlaps the campaign end; destination starts 0.631093 seconds after it and remains in the explicitly authorized seven-boundary exception set"},
)

RATIONALE = (
    "Observed-flow y_stage regresses to Benign within or at the sampled edge of an independently "
    "declared corrected-rule campaign interval. Reviewer option (c) excludes only this boundary from CRF structured training "
    "loss; stage cross-entropy, targets, Viterbi decoding, transition policy, and illegal-transition "
    "metrics remain unchanged. This is a dataset-specific objective exception, not a general relaxation."
)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def close(left, right) -> bool:
    return abs(float(left) - float(right)) < 1e-6


def annotate(samples, split: str):
    transitions = {item["id"]: 0 for item in BOUNDARIES}
    modeled = {item["id"]: 0 for item in BOUNDARIES}
    state_occurrences = {item["id"]: 0 for item in BOUNDARIES}
    seen = set()
    for sample in samples:
        for destination_index, (source, destination) in enumerate(zip(sample.states, sample.states[1:]), start=1):
            for item in BOUNDARIES:
                if (close(source.metadata["window_start"], item["source_window_start"])
                        and close(destination.metadata["window_start"], item["destination_window_start"])):
                    if (source.y_stage, destination.y_stage) != (item["source_stage"], item["destination_stage"]):
                        raise ValueError(f"{split}/{item['id']}: reviewed stage pair changed")
                    source_inside = (item["campaign_start_epoch"] <= source.metadata["window_start"]
                                     < item["campaign_end_epoch"])
                    destination_inside_or_source_overlaps_end = (
                        destination.metadata["window_start"] <= item["campaign_end_epoch"]
                        or item["campaign_end_epoch"] <= source.metadata["window_end"])
                    if not (source_inside and destination_inside_or_source_overlaps_end):
                        raise ValueError(f"{split}/{item['id']}: boundary no longer relates to the cited campaign")
                    transitions[item["id"]] += 1
                    # CRF tags are sample.states[1:], so state[0] -> state[1]
                    # is not an edge in the structured target.
                    modeled[item["id"]] += int(destination_index >= 2)
        for state in sample.states:
            for item in BOUNDARIES:
                if close(state.metadata["window_start"], item["destination_window_start"]):
                    state_occurrences[item["id"]] += 1
                    key = (id(state), item["id"])
                    if key in seen:
                        continue
                    seen.add(key)
                    if state.y_stage != item["destination_stage"] or state.metadata.get("campaign_reset", False):
                        raise ValueError(f"{split}/{item['id']}: destination is not the reviewed non-reset target")
                    state.metadata.update({
                        "crf_transition_loss_excluded": True,
                        "crf_transition_loss_exclusion_id": item["id"],
                        "crf_transition_loss_exclusion_pair": item["pair"],
                        "crf_transition_loss_exclusion_rationale": RATIONALE,
                        "crf_transition_loss_exclusion_campaign": item["campaign"],
                        "crf_transition_loss_exclusion_campaign_interval_epoch": [
                            item["campaign_start_epoch"], item["campaign_end_epoch"]],
                        "crf_transition_loss_exclusion_source": (
                            f"Distrinet corrected rules, commit {RULE_COMMIT}"),
                        "crf_transition_loss_exclusion_source_url": RULE_URL,
                        "crf_transition_loss_exclusion_source_file": str(RULE_FILE.relative_to(ROOT)),
                        "crf_transition_loss_exclusion_source_sha256": digest(RULE_FILE),
                        "crf_transition_loss_exclusion_reviewer_decision": DECISION,
                    })
    declared = [key for key, count in transitions.items() if count]
    if split == "train" and set(declared) != {item["id"] for item in BOUNDARIES}:
        raise ValueError(f"train: missing reviewed boundaries: {declared}")
    if split != "train" and declared:
        raise ValueError(f"{split}: option-(c) exclusions unexpectedly present")
    return {"transition_occurrences": transitions, "modeled_crf_edge_occurrences": modeled,
            "destination_state_occurrences": state_occurrences, "declared_boundary_ids": declared}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed_real_chunk_r4_reviewed_resets")
    parser.add_argument("--output", default="data/processed_real_chunk_r4_option_c")
    parser.add_argument("--audit", default="examples/real_data_validation/r4/crf_loss_exclusion_provenance.json")
    args = parser.parse_args()
    source, output, audit_path = ROOT / args.input, ROOT / args.output, ROOT / args.audit
    partial = output.with_name(output.name + ".partial")
    if output.exists() or partial.exists() or audit_path.exists():
        raise FileExistsError("Preserve existing option-(c) derivative, partial output, and provenance")
    partial.mkdir(parents=True)
    try:
        shutil.copy2(source / "normalization.json", partial / "normalization.json")
        reports = {}
        for split in ("train", "val", "test"):
            samples = torch.load(source / f"{split}.pt", map_location="cpu", weights_only=False)
            reports[split] = annotate(samples, split)
            torch.save(samples, partial / f"{split}.pt")
        metadata = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
        metadata["crf_transition_loss_exclusions"] = {
            "reviewer_decision": DECISION, "scope": "CRF training loss only",
            "boundaries": list(BOUNDARIES), "rationale": RATIONALE,
            "transition_policy_changed": False, "viterbi_changed": False,
            "illegal_transition_metric_changed": False, "stage_cross_entropy_changed": False,
            "rule_source_url": RULE_URL, "rule_source_sha256": digest(RULE_FILE),
        }
        (partial / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        partial.replace(output)
        audit = {
            "status": "complete", "reviewer_decision": DECISION,
            "input": args.input, "output": args.output,
            "scope": "CRF training loss only", "boundaries": list(BOUNDARIES),
            "rationale": RATIONALE, "split_reports": reports,
            "transition_policy_changed": False, "viterbi_changed": False,
            "illegal_transition_metric_changed": False, "stage_cross_entropy_changed": False,
            "rule_source_url": RULE_URL, "rule_source_sha256": digest(RULE_FILE),
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
