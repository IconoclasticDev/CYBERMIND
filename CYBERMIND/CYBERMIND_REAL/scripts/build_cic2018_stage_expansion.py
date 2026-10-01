#!/usr/bin/env python3
"""Add the two corrected February 28 victim captures to the audited corpus."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cybermind.data.pcap_extract import PACKET_FEATURES
from cybermind.data.real_chunk_export import export_capture
from cybermind.data.real_chunk_label import (
    CORRECTED_SOURCE,
    LABEL_METHOD,
    ORIGINAL_SOURCE,
    corrected_labels,
    original_labels,
    stage_for_label,
)

ARCHIVE = ROOT / "data/raw/CIC-IDS-2018/Original Network Traffic and Log data/Wednesday-28-02-2018/pcap.zip"
MEMBERS = (
    ("pcap/capEC2AMAZ-O4EL3NG-172.31.69.24- part1", 98_445_934, 0x3223406F),
    ("pcap/capEC2AMAZ-O4EL3NG-172.31.69.24-part2", 347_870_553, 0xD37480B8),
)
BASE_LABELS = ROOT / "data/real_chunk/labeled"
EXPANSION = ROOT / "data/stage_expansion"
MANIFEST = ROOT / "results/stage_expansion/rebuild_manifest.json"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def add_base_corpus() -> list[str]:
    linked = []
    for source in sorted(BASE_LABELS.rglob("*.csv")):
        destination = EXPANSION / "labeled" / source.relative_to(BASE_LABELS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if not os.path.samefile(source, destination):
                raise ValueError(f"Expansion path is not the audited base artifact: {destination}")
        else:
            os.link(source, destination)
        linked.append(str(destination.relative_to(ROOT)))
    if len(linked) != 15:
        raise ValueError(f"Expected 15 audited base captures, found {len(linked)}")
    return linked


def extract_member(bundle: zipfile.ZipFile, member: str, size: int, crc: int) -> tuple[Path, str]:
    info = bundle.getinfo(member)
    if info.file_size != size or info.CRC != crc:
        raise ValueError(f"Pinned archive member metadata changed: {member}")
    destination = EXPANSION / "captures" / Path(member).name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        partial = destination.with_name(destination.name + ".partial")
        if partial.exists():
            raise FileExistsError(f"Preserve incomplete extraction: {partial}")
        with bundle.open(info) as source, partial.open("xb") as target:
            shutil.copyfileobj(source, target, length=8 * 1024 * 1024)
        if partial.stat().st_size != size:
            raise ValueError(f"Extracted size mismatch: {member}")
        partial.replace(destination)
    if destination.stat().st_size != size:
        raise ValueError(f"Existing capture size mismatch: {destination}")
    return destination, digest(destination)


def label_flow_csv(source: Path, destination: Path) -> tuple[int, Counter]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".partial")
    if destination.exists():
        counts = Counter()
        rows = 0
        for frame in pd.read_csv(destination, chunksize=100_000, low_memory=False):
            rows += len(frame)
            counts.update(frame["label"].astype(str))
        return rows, counts
    if partial.exists():
        raise FileExistsError(f"Preserve incomplete labeling output: {partial}")
    first, rows, counts = True, 0, Counter()
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
        counts.update(labeled.label.astype(str))
    if rows == 0:
        raise ValueError(f"No labeled flows produced from {source}")
    partial.replace(destination)
    return rows, counts


def validate_output(path: Path, expected_rows: int) -> None:
    rows = 0
    required = {"timestamp", "src", "dst", "label", "stage", "infiltration", *PACKET_FEATURES}
    for frame in pd.read_csv(path, chunksize=100_000, low_memory=False):
        if required.difference(frame.columns):
            raise ValueError(f"Missing required columns: {path}")
        expected = stage_for_label(frame.label.astype(str))
        actual = pd.to_numeric(frame.stage, errors="raise").astype("int64")
        if not actual.equals(expected):
            raise ValueError(f"Stage labels failed semantic validation: {path}")
        rows += len(frame)
    if rows != expected_rows:
        raise ValueError(f"Row count changed during labeling: {path}")


def main() -> None:
    if not ARCHIVE.is_file():
        raise FileNotFoundError(ARCHIVE)
    linked = add_base_corpus()
    records = []
    with zipfile.ZipFile(ARCHIVE) as bundle:
        for member, size, crc in MEMBERS:
            capture, capture_hash = extract_member(bundle, member, size, crc)
            stem = Path(member).name.replace(" ", "_")
            flow = EXPANSION / "flows/2018-02-28" / f"{stem}.csv"
            report = ROOT / "results/stage_expansion/exports" / f"{stem}.json"
            if not flow.exists():
                export_capture(capture, flow, report, capture_date="2018-02-28",
                               capture_member=member, expected_sha256=capture_hash)
            labeled = EXPANSION / "labeled/2018-02-28" / f"{stem}.csv"
            rows, counts = label_flow_csv(flow, labeled)
            validate_output(labeled, rows)
            records.append({
                "archive": str(ARCHIVE.relative_to(ROOT)), "member": member,
                "member_bytes": size, "member_crc32": f"{crc:08x}",
                "capture": str(capture.relative_to(ROOT)), "capture_sha256": capture_hash,
                "flow": str(flow.relative_to(ROOT)), "flow_sha256": digest(flow),
                "labeled": str(labeled.relative_to(ROOT)), "labeled_sha256": digest(labeled),
                "rows": rows, "labels": dict(sorted(counts.items())),
            })
    atomic_json(MANIFEST, {
        "status": "complete", "scope": "two corrected CIC-IDS2018 February 28 victim captures",
        "base_artifacts": linked, "added_artifacts": records,
        "label_source": CORRECTED_SOURCE, "original_schedule_source": ORIGINAL_SOURCE,
        "limitations": [
            "These captures add verified infiltration, reconnaissance, and victim-attacker communication examples.",
            "They do not establish verified lateral-movement or exfiltration labels.",
        ],
    })
    print(json.dumps({"status": "complete", "added": records}, indent=2), flush=True)


if __name__ == "__main__":
    main()
