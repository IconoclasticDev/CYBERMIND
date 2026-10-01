#!/usr/bin/env python3
"""Gate training on stage coverage in the expanded chronological split."""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cybermind.data.dataset import GraphSequenceDataset


def counts(path: Path) -> list[int]:
    result = Counter(
        state.y_stage
        for sample in GraphSequenceDataset(path)
        for state in sample.states[1:]
    )
    return [result.get(stage, 0) for stage in range(7)]


def main() -> None:
    processed = ROOT / "data/processed_stage_expansion"
    report = {split: counts(processed / f"{split}.pt") for split in ("train", "val", "test")}
    missing_train = [stage for stage in (0, 1, 2, 4) if report["train"][stage] == 0]
    if missing_train:
        raise ValueError(f"Expanded training split still lacks required supported stages: {missing_train}")
    if report["val"][4] == 0 or report["test"][4] == 0:
        raise ValueError("C2 must remain in both chronological validation and test splits")
    output = ROOT / "results/stage_expansion/stage_coverage.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "target_occurrences": report,
        "taxonomy": {"0": "benign", "1": "recon", "2": "initial access",
                     "3": "lateral movement", "4": "C2", "5": "exfiltration", "6": "unknown"},
        "unsupported_by_source_evidence": [3, 5],
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
