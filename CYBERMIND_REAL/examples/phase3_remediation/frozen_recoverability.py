"""Read-only generative-structure audit of the ORIGINAL frozen smoke tensors.

No classifier, feature, generator, label, or gate changes are made. Empirical
counts are distinct from assumptions about the stochastic generating process.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
SOURCE = ROOT / "examples/smoke/baseline_before/processed"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(values):
    return dict(sorted(Counter(values).items()))


def main():
    sources = [ROOT / "scripts/make_synthetic.py", ROOT / "src/cybermind/models/world_model.py",
               *sorted(SOURCE.glob("*.pt"))]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in sources}
    splits = {name: torch.load(SOURCE / f"{name}.pt", map_location="cpu", weights_only=False)
              for name in ("train", "val", "test")}
    result = {
        "purpose": "Read-only structural recoverability audit; NOT a classifier, model result, or exit gate",
        "source": str(SOURCE.relative_to(ROOT)),
        "fixture_mutated": False,
        "synthetic_only": True,
        "generator": {
            "path": "scripts/make_synthetic.py",
            "sequence_count": 24,
            "sequence_length": 8,
            "node_count_rule": "8 + (i % 4)",
            "attack_rule": "i % 3 == 0 and t >= seq // 2",
            "stage_rule": "5 if attack and t >= seq - 2, otherwise 2 if attack, otherwise 0",
            "node_features": "torch.rand(nodes, node_dim), freshly sampled at each timestep",
            "edge_attributes": "torch.rand(number_of_edges, 7), freshly sampled at each timestep",
            "topology": "all ordered-as-increasing-index node combinations of size 2; determined only by node count",
            "generator_does_not_condition_feature_distributions_on_attack_or_stage": True,
            "model_encode_state_inputs": ["state.x", "state.edge_index", "state.edge_attr"],
            "scenario_id_and_stage_labels_are_not_encoder_inputs": True,
            "statistical_interpretation": "Under the torch.rand sampling mechanism, conditional on node count and temporal position, node/edge feature distributions have the same support for attack and benign sequences. The hidden i % 3 assignment is not supplied to the encoder.",
        },
        "splits": {},
    }
    training_node_counts = set()
    for split, samples in splits.items():
        by_nodes = defaultdict(list)
        fingerprints = []
        for sample in samples:
            by_nodes[len(sample.states[0].x)].append(sample)
            visible = hashlib.sha256()
            for state in sample.states[:-1]:
                for attr in (state.x, state.edge_index, state.edge_attr):
                    visible.update(attr.numpy().tobytes())
            fingerprints.append(visible.hexdigest())
        if split == "train":
            training_node_counts = set(by_nodes)
        groups = {}
        for node_count, items in sorted(by_nodes.items()):
            groups[str(node_count)] = {
                "sequence_count": len(items),
                "attack_sequence_count": sum(any(s.y_infiltration for s in item.states) for item in items),
                "final_stage_counts": counts(int(item.states[-1].y_stage) for item in items),
                "supervision_stage_counts_states_1_to_7": counts(int(s.y_stage) for item in items for s in item.states[1:]),
                "both_attack_and_benign_sequences_present": len({bool(any(s.y_infiltration for s in item.states)) for item in items}) == 2,
                "scenario_ids_for_audit_only": [item.scenario_id for item in items],
            }
        result["splits"][split] = {
            "sequence_count": len(samples),
            "stored_lengths": sorted({len(s.states) for s in samples}),
            "observed_lengths_original_rollout": sorted({len(s.states[:-1]) for s in samples}),
            "node_counts": sorted(by_nodes),
            "node_counts_seen_in_train": sorted(set(by_nodes) & training_node_counts),
            "all_node_counts_seen_in_train": set(by_nodes) <= training_node_counts,
            "node_count_groups": groups,
            "all_window_stage_counts": counts(int(s.y_stage) for item in samples for s in item.states),
            "training_target_stage_counts_states_1_to_7": counts(int(s.y_stage) for item in samples for s in item.states[1:]),
            "original_forecast_step_1_target_counts": counts(int(item.states[-1].y_stage) for item in samples),
            "attack_sequence_count": sum(any(s.y_infiltration for s in item.states) for item in samples),
            "unique_observed_input_fingerprints": len(set(fingerprints)),
            "per_step_stored_target_availability": [
                {"step": step, "observed_last_t": 6, "forecast_target_t": 6 + step,
                 "actual_target_count": len(samples) if step == 1 else 0,
                 "actual_target_stage_counts": counts(int(item.states[-1].y_stage) for item in samples) if step == 1 else {},
                 "note": "Existing target at t=7" if step == 1 else "Beyond this generator's eight stored timesteps; no future labels manufactured"}
                for step in range(1, 5)
            ],
        }
    # This is a count bound for this finite training sample using node count alone,
    # not a trained artifact and not a bound on arbitrary memorization of tensors.
    correct = sum(max(Counter(int(item.states[-1].y_stage) for item in items).values())
                  for items in (group for group in (
                      [sample for sample in splits["train"] if len(sample.states[0].x) == n]
                      for n in training_node_counts)))
    result["node_count_only_training_final_target_majority_accuracy"] = {
        "correct": correct, "total": len(splits["train"]), "accuracy": correct / len(splits["train"]),
        "interpretation": "Empirical node-count-only majority ceiling on training final targets; not a model evaluation or general upper bound",
    }
    result["conclusions"] = [
        "Unlike the periodic-byte original integration fixture, no deterministic stage signal is deliberately present in the frozen random feature values.",
        "Every training node count contains both attack and benign sequences; node count cannot uniquely recover the hidden attack assignment.",
        "All validation/test node counts overlap training, but overlapping support does not reveal the hidden i % 3 assignment or guarantee stage prediction on fresh samples.",
        "Input tensors are distinct and finite, so a sufficiently flexible model could memorize them or exploit accidental correlations; this audit does not prove that the saved finite test tensors are unclassifiable.",
        "Under fresh independent random draws, feature values alone contain no intended information about the attack flag conditional on node count. Diverse outputs on random tensors would not establish correct stage generalization.",
        "Temporal position can determine whether an attack sequence would be at Initial Access or Exfiltration, but does not supply whether the sequence belongs to the attack subgroup.",
        "Only forecast step 1 has an actual stored target. Diversity and transition legality can still be measured at steps 2-4, but accuracy there cannot be established from these eight-state samples without adding labels.",
    ]
    after = {str(p.relative_to(ROOT)): digest(p) for p in sources}
    assert after == hashes
    result["source_sha256_before_and_after"] = hashes
    result["original_sources_unchanged"] = True
    destination = Path(__file__).with_name("frozen_recoverability.json")
    destination.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
