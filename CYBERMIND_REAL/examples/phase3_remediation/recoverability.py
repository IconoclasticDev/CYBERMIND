"""Read-only structural signal diagnostic; never used as a model or exit gate.

Fit the affine coordinate/time relation and label period using TRAIN ONLY, then
evaluate it on untouched validation/test tensors. This establishes information
presence, not neural learnability, forecasting performance, or generalization.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
SOURCE = ROOT / "examples/phase3_root_cause/original_pipeline"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique_states(samples):
    indexed = {(s.scenario_id, s.timestamp): s for sample in samples for s in sample.states}
    return sorted(indexed.values(), key=lambda s: (s.scenario_id, s.timestamp))


def main():
    paths = [SOURCE / "config.yaml", *sorted((SOURCE / "processed").glob("*"))]
    before = {str(p.relative_to(ROOT)): digest(p) for p in paths if p.is_file()}
    samples = {split: torch.load(SOURCE / "processed" / f"{split}.pt",
                                map_location="cpu", weights_only=False)
               for split in ("train", "val", "test")}
    states = {split: unique_states(items) for split, items in samples.items()}
    cfg = yaml.safe_load((SOURCE / "config.yaml").read_text())
    norm = json.loads((SOURCE / "processed/normalization.json").read_text())
    column = norm["node"]["features"].index("bytes_total")
    train = states["train"]
    origin = min(s.timestamp for s in train)
    train_seconds = np.array([s.timestamp - origin for s in train])
    train_coordinate = np.array([float(s.x[0, column]) for s in train])
    design = np.column_stack((train_seconds, np.ones(len(train_seconds))))
    slope, intercept = np.linalg.lstsq(design, train_coordinate, rcond=None)[0]
    labels = np.array([s.y_stage for s in train], dtype=int)
    # Choose the shortest period with >= 3 complete repetitions using train only.
    period = None
    periodic_labels = None
    for candidate in range(1, len(train) // 3 + 1):
        table = {}
        valid = True
        for second, label in zip(train_seconds.astype(int), labels):
            residue = int(second % candidate)
            if residue in table and table[residue] != int(label):
                valid = False
                break
            table[residue] = int(label)
        if valid and len(table) == candidate:
            period, periodic_labels = candidate, table
            break
    assert period is not None, "Training labels have no tested exact periodic rule"

    def reconstructed_second(state):
        return (float(state.x[0, column]) - intercept) / slope

    def analytical_label(second):
        return periodic_labels[int(np.rint(second)) % period]

    policy = yaml.safe_load((ROOT / "knowledge/stage_mapping.yaml").read_text())
    allowed = np.asarray(policy["transition_matrix"], dtype=bool)
    reset_allowed = np.asarray(policy["reset_transition_matrix"], dtype=bool)
    result = {
        "purpose": "Structural recoverability diagnostic only; NOT a model result or exit-criterion gate",
        "source": str(SOURCE.relative_to(ROOT)),
        "synthetic_only": True,
        "fixture_mutated": False,
        "prototype_features_added": False,
        "training_only_fit": True,
        "actual_history": {
            "configured_states": cfg["data"]["history"],
            "stored_lengths": sorted({len(s.states) for items in samples.values() for s in items}),
            "forecast_observed_lengths": sorted({len(s.states[:-1]) for items in samples.values() for s in items}),
            "forecast_reference": "examples/phase3_root_cause/inspect_rollouts.py: states=sample.states[:-1]",
            "pdf_history_eight_matches_original": cfg["data"]["history"] == 8,
        },
        "train_fit": {
            "feature": f"state.x[0,{column}] (train-normalized bytes_total)",
            "model_directly_receives_timestamp_or_stage_label": False,
            "timestamp_used_for_diagnostic_affine_fit_only": True,
            "seconds_origin": origin,
            "normalized_coordinate_per_second": float(slope),
            "normalized_coordinate_at_origin": float(intercept),
            "minimum_exact_period_seconds": period,
            "residue_stage_mapping": periodic_labels,
            "max_period_tested": len(train) // 3,
            "period_fitting_rule": "smallest period with exact train agreement and at least three repetitions",
        },
        "splits": {},
        "limitations": [
            "The diagnostic uses an explicit affine reconstruction and periodic rule; neither is added to the model, features, loss, or gate.",
            "Validation/test agreement demonstrates retained input information in this deterministic fixture, not that the current encoder/transition network can learn extrapolation.",
            "Four-step future targets use only already-stored windows in the same split; missing boundary futures are excluded and counted, never synthesized.",
            "Timestamp and labels calibrate/evaluate this diagnostic; actual model-visible inputs remain x, edge_index, and edge_attr only.",
            "Exact periodic labels can include Recon-to-Benign backwards transitions requiring explicit campaign-reset metadata under the unchanged policy.",
        ],
    }
    for split, windows in states.items():
        seconds = np.array([s.timestamp - origin for s in windows])
        reconstructed = np.array([reconstructed_second(s) for s in windows])
        prediction = np.array([analytical_label(t) for t in reconstructed])
        actual = np.array([s.y_stage for s in windows])
        x = np.stack([s.x.numpy() for s in windows])
        edge = np.stack([s.edge_attr.numpy() for s in windows])
        lookup = {(s.scenario_id, s.timestamp): s for s in windows}
        coordinate = np.array([float(s.x[0, column]) for s in windows])
        records = []
        for step in range(1, 5):
            correct = 0
            observed = []
            target_stages = []
            base_illegal = reset_unresolved = reset_declared = 0
            for sample in samples[split]:
                last = sample.states[:-1][-1]
                target = lookup.get((last.scenario_id, last.timestamp + step))
                previous = lookup.get((last.scenario_id, last.timestamp + step - 1))
                if target is None or previous is None:
                    continue
                inferred = analytical_label(reconstructed_second(last) + step)
                correct += int(inferred == target.y_stage)
                observed.append(inferred)
                target_stages.append(int(target.y_stage))
                illegal = not allowed[previous.y_stage, target.y_stage]
                declared = bool(target.metadata.get("campaign_reset", False))
                base_illegal += int(illegal)
                reset_declared += int(declared)
                reset_unresolved += int(illegal and not (declared and reset_allowed[previous.y_stage, target.y_stage]))
            records.append({
                "step": step,
                "available_actual_targets": len(observed),
                "boundary_futures_excluded": len(samples[split]) - len(observed),
                "analytical_reconstruction_correct": correct,
                "analytical_reconstruction_accuracy": correct / len(observed),
                "analytical_distinct_non_unknown": len(set(observed) - {6}),
                "actual_target_stage_histogram": dict(Counter(target_stages)),
                "actual_target_incoming_illegal_without_resets": base_illegal,
                "actual_target_declared_reset_count": reset_declared,
                "actual_target_incoming_illegal_after_existing_metadata": reset_unresolved,
            })
        result["splits"][split] = {
            "sequence_count": len(samples[split]),
            "unique_windows": len(windows),
            "relative_seconds_range": [float(seconds.min()), float(seconds.max())],
            "normalized_coordinate_range": [float(coordinate.min()), float(coordinate.max())],
            "windows_outside_train_coordinate_range": int(((coordinate < train_coordinate.min()) | (coordinate > train_coordinate.max())).sum()),
            "max_absolute_reconstructed_second_error": float(np.abs(reconstructed - seconds).max()),
            "minimum_adjacent_normalized_coordinate_gap": float(np.diff(coordinate).min()),
            "rounded_second_reconstruction_correct": int((np.rint(reconstructed) == seconds).sum()),
            "analytical_current_stage_correct": int((prediction == actual).sum()),
            "analytical_current_stage_accuracy": float((prediction == actual).mean()),
            "node_feature_columns_varying_over_time": np.flatnonzero(np.ptp(x, axis=0).max(axis=0) > 0).tolist(),
            "edge_feature_columns_varying_over_time": np.flatnonzero(np.ptp(edge, axis=0).max(axis=0) > 0).tolist(),
            "all_graph_topologies_identical": all(torch.equal(windows[0].edge_index, s.edge_index) for s in windows),
            "per_step_diagnostic": records,
        }
    after = {str(p.relative_to(ROOT)): digest(p) for p in paths if p.is_file()}
    assert before == after
    result["original_source_sha256_before_and_after"] = before
    result["original_sources_unchanged"] = True
    result["conclusion"] = (
        "Existing normalized byte coordinates preserve sufficient precision to reconstruct the periodic stage labels, "
        "including four-step futures where actual stored targets exist. Information absence is not established. "
        "The current model must learn a periodic relation and extrapolate beyond the training coordinate range; "
        "this analytical diagnostic does not demonstrate that it does so."
    )
    target = Path(__file__).with_name("recoverability.json")
    target.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
