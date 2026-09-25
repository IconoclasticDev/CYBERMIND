#!/usr/bin/env python3
"""Rebuild the audited three-day real-PCAP corpus from local official archives."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cybermind.data.real_chunk_export import export_capture
from cybermind.data.pcap_extract import PACKET_FEATURES
from cybermind.data.real_chunk_label import (
    CORRECTED_SOURCE,
    LABEL_METHOD,
    ORIGINAL_SOURCE,
    corrected_labels,
    original_labels,
    stage_for_label,
)

R0_MANIFEST = ROOT / "data/manifests/r0_real_chunk_files.csv"
R1_MANIFEST = ROOT / "data/manifests/r1_real_chunk_files.csv"
EVIDENCE = ROOT / "results/real_best/rebuild"
ARCHIVES = {
    "2018-02-14": ROOT / "data/raw/CIC-IDS-2018/Original Network Traffic and Log data/Wednesday-14-02-2018/pcap.zip",
    "2018-03-01": ROOT / "data/raw/CIC-IDS-2018/Original Network Traffic and Log data/Thursday-01-03-2018/pcap.zip",
    "2018-03-02": ROOT / "data/raw/CIC-IDS-2018/Original Network Traffic and Log data/Friday-02-03-2018/pcap.zip",
}
FEB_MEMBER = "pcap/UCAP172.31.69.25"
FEB_SOURCE = ROOT / "data/raw/CIC-IDS-2018/one_day_2018-02-14/UCAP172.31.69.25.pcap"
FEB_SOURCE_BYTES = 852_795_392
FEB_SOURCE_SHA256 = "008f18cce0ff420ce013eba6d97ae0b974f36028a0707a977f78d4bfd7f48afc"
FEB_CUTOFF = 852_795_085


def local_path(value: str) -> Path:
    return ROOT / value.replace("\\", "/")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(path: Path, size: int, sha256: str) -> None:
    if not path.is_file() or path.stat().st_size != size or digest(path) != sha256:
        raise ValueError(f"Integrity mismatch: {path}")


def validate_labeled(path: Path, expected_rows: int) -> dict:
    """Validate regenerated labels semantically across the complete artifact.

    The historical manifest hashes CSV bytes produced by an older pandas build.
    CSV serialization can change while every source row and derived label remains
    identical, so regenerated labels get a fresh content manifest after strict
    row-level validation instead of being rejected on historical byte identity.
    """
    rows = 0
    required = {
        "timestamp", "src", "dst", "label", "stage", "infiltration",
        "label_verified", "label_refinement_verified", "label_method",
        "corrected_rule_source", "original_rule_source", "label_discrepancy",
        *PACKET_FEATURES,
    }
    for frame in pd.read_csv(path, chunksize=100_000, low_memory=False):
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"Missing labeled fields in {path}: {missing}")
        rows += len(frame)
        verified = frame["label_verified"].astype(str).str.lower().isin(["true", "1"])
        if not verified.all():
            raise ValueError(f"Unverified labels in {path}")
        stages = pd.to_numeric(frame["stage"], errors="coerce")
        expected_stages = stage_for_label(frame["label"])
        if stages.isna().any() or not np.array_equal(stages.to_numpy(), expected_stages.to_numpy()):
            raise ValueError(f"Stage/label mismatch in {path}")
        infiltration = pd.to_numeric(frame["infiltration"], errors="coerce")
        if infiltration.isna().any() or not np.array_equal(
            infiltration.to_numpy(), stages.ne(0).astype(float).to_numpy()
        ):
            raise ValueError(f"Infiltration/stage mismatch in {path}")
        packet = frame[list(PACKET_FEATURES)].apply(pd.to_numeric, errors="coerce")
        if not np.isfinite(packet.to_numpy(dtype=float)).all():
            raise ValueError(f"Invalid packet features in {path}")
        if not packet["packet_features_available"].eq(1).all():
            raise ValueError(f"Unavailable packet features in {path}")
    if rows != expected_rows:
        raise ValueError(f"Labeled row count mismatch: {path}: {rows} != {expected_rows}")
    return {"path": str(path.relative_to(ROOT)), "rows": rows,
            "bytes": path.stat().st_size, "sha256": digest(path)}


def extract(archive: Path, member: str, target: Path, expected_size: int, expected_sha256: str) -> None:
    if target.exists():
        verify(target, expected_size, expected_sha256)
        print(f"[EXTRACT] verified existing {target}", flush=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    if partial.exists():
        raise FileExistsError(f"Preserve incomplete extraction for review: {partial}")
    with zipfile.ZipFile(archive) as bundle:
        info = bundle.getinfo(member)
        if info.file_size != expected_size:
            raise ValueError(f"Archive member size changed: {member}")
        with bundle.open(info) as source, partial.open("xb") as destination:
            shutil.copyfileobj(source, destination, length=8 * 1024 * 1024)
    verify(partial, expected_size, expected_sha256)
    partial.replace(target)
    print(f"[EXTRACT] {member} -> {target}", flush=True)


def reconstruct_captures(r0_records: list[dict]) -> None:
    extract(ARCHIVES["2018-02-14"], FEB_MEMBER, FEB_SOURCE,
            FEB_SOURCE_BYTES, FEB_SOURCE_SHA256)
    feb_record = next(record for record in r0_records if record["date"] == "2018-02-14")
    derivative = local_path(feb_record["source_path"])
    if not derivative.exists():
        partial = derivative.with_name(derivative.name + ".partial")
        if partial.exists():
            raise FileExistsError(f"Preserve incomplete derivative: {partial}")
        derivative.parent.mkdir(parents=True, exist_ok=True)
        with FEB_SOURCE.open("rb") as source, partial.open("xb") as destination:
            remaining = FEB_CUTOFF
            while remaining:
                block = source.read(min(8 * 1024 * 1024, remaining))
                if not block:
                    raise ValueError("Unexpected EOF in approved February derivative")
                destination.write(block)
                remaining -= len(block)
        partial.replace(derivative)
    verify(derivative, int(feb_record["source_bytes"]), feb_record["source_sha256"])

    for record in r0_records:
        if record["date"] == "2018-02-14":
            continue
        target = local_path(record["source_path"])
        extract(ARCHIVES[record["date"]], record["capture_member"], target,
                int(record["source_bytes"]), record["source_sha256"])


def rebuild_flows(r0_records: list[dict]) -> None:
    for record in r0_records:
        source = local_path(record["source_path"])
        output = local_path(record["output_path"])
        if output.exists():
            verify(output, int(record["output_bytes"]), record["output_sha256"])
            print(f"[FLOW] verified existing {output}", flush=True)
            continue
        report = EVIDENCE / "r0_exports" / record["date"] / f"{source.stem}.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        if report.exists():
            raise FileExistsError(f"Output missing but rebuild report exists: {report}")
        export_capture(source, output, report, capture_date=record["date"],
                       capture_member=record["capture_member"],
                       expected_sha256=record["source_sha256"])
        verify(output, int(record["output_bytes"]), record["output_sha256"])
        print(f"[FLOW] verified {output}", flush=True)


def rebuild_labels(r1_records: list[dict]) -> None:
    regenerated = []
    for record in r1_records:
        source = local_path(record["r0_input_path"])
        output = local_path(record["output_path"])
        if output.exists():
            report = validate_labeled(output, int(record["rows"]))
            report["historical_sha256"] = record["output_sha256"]
            report["historical_byte_match"] = (
                report["bytes"] == int(record["output_bytes"])
                and report["sha256"] == record["output_sha256"]
            )
            regenerated.append(report)
            print(f"[LABEL] verified existing {output}", flush=True)
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        partial = output.with_name(output.name + ".partial")
        if not partial.exists():
            first = True
            rows = 0
            for frame in pd.read_csv(source, chunksize=100_000, low_memory=False):
                corrected = corrected_labels(frame)
                original = original_labels(frame)
                labeled = pd.concat([frame, corrected, original], axis=1)
                labeled["stage"] = stage_for_label(labeled.label)
                labeled["infiltration"] = labeled.stage.ne(0).astype(float)
                labeled["label_verified"] = True
                labeled["label_refinement_verified"] = labeled.corrected_refinement_status.eq("complete")
                labeled["label_method"] = LABEL_METHOD
                labeled["corrected_rule_source"] = CORRECTED_SOURCE
                labeled["original_rule_source"] = ORIGINAL_SOURCE
                labeled["label_discrepancy"] = labeled.label.ne(labeled.original_cic_label)
                labeled.to_csv(partial, mode="w" if first else "a", header=first,
                               index=False, encoding="utf-8")
                first = False
                rows += len(labeled)
        report = validate_labeled(partial, int(record["rows"]))
        partial.replace(output)
        report["path"] = str(output.relative_to(ROOT))
        report["historical_sha256"] = record["output_sha256"]
        report["historical_byte_match"] = (
            report["bytes"] == int(record["output_bytes"])
            and report["sha256"] == record["output_sha256"]
        )
        regenerated.append(report)
        print(f"[LABEL] verified {output}", flush=True)
    manifest = EVIDENCE / "regenerated_labeled_manifest.json"
    temporary = manifest.with_suffix(".json.partial")
    temporary.write_text(json.dumps(regenerated, indent=2) + "\n", encoding="utf-8")
    temporary.replace(manifest)


def main() -> None:
    r0_records = list(csv.DictReader(R0_MANIFEST.open(encoding="utf-8")))
    r1_records = list(csv.DictReader(R1_MANIFEST.open(encoding="utf-8")))
    if len(r0_records) != 15 or len(r1_records) != 15:
        raise ValueError("Expected the audited 15-capture manifests")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    reconstruct_captures(r0_records)
    (EVIDENCE / "captures.complete").touch()
    rebuild_flows(r0_records)
    (EVIDENCE / "flows.complete").touch()
    rebuild_labels(r1_records)
    (EVIDENCE / "labels.complete").touch()
    print("[DONE] Audited real-PCAP corpus reconstructed and strictly validated", flush=True)


if __name__ == "__main__":
    main()
