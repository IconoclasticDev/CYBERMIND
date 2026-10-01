#!/usr/bin/env python3
"""Build a portable, GitHub-sized CYBERMIND SIH submission package."""
from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
PROJECT = REPO / "CYBERMIND" / "CYBERMIND_REAL"
RELEASES = REPO / "CYBERMIND" / "releases"
ARCHIVE = RELEASES / "CYBERMIND_SIH_SUBMISSION_2026-09-26.zip"
EXTERNAL_MANIFEST = RELEASES / "CYBERMIND_SIH_SUBMISSION_2026-09-26.manifest.json"
PREFIX = "CYBERMIND_SIH_SUBMISSION"
MAX_BYTES = 95_000_000


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def included(relative: str) -> bool:
    if relative in {"README.md", "CYBERMIND/deliverables/pdf/CYBERMIND_Final_Implementation_Plan.pdf"}:
        return True
    if not relative.startswith("CYBERMIND/CYBERMIND_REAL/"):
        return False
    inside = relative.removeprefix("CYBERMIND/CYBERMIND_REAL/")
    if inside.startswith("data/"):
        return inside.startswith("data/manifests/")
    if inside.startswith("checkpoints/"):
        return inside == "checkpoints/final_grouped/best.pt"
    if inside.startswith("results/"):
        return inside.startswith("results/final_grouped/")
    if inside.startswith("examples/"):
        return False
    return True


def main():
    RELEASES.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO).split(b"\0")
    paths = sorted({raw.decode() for raw in tracked if raw and included(raw.decode())})
    # Include this builder and the package guide when invoked before their first commit.
    for relative in ("CYBERMIND/CYBERMIND_REAL/scripts/build_sih_submission_zip.py",
                     "CYBERMIND/releases/CYBERMIND_SIH_PACKAGE_README.md"):
        if (REPO / relative).is_file() and relative not in paths:
            paths.append(relative)
    paths.sort()
    records = []
    for relative in paths:
        path = REPO / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        data = path.read_bytes()
        records.append({"path": relative, "bytes": len(data), "sha256": sha256_bytes(data)})
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    internal = {
        "package": PREFIX,
        "source_commit": source_commit,
        "selected_checkpoint": "CYBERMIND/CYBERMIND_REAL/checkpoints/final_grouped/best.pt",
        "included_files": len(records),
        "uncompressed_bytes": sum(record["bytes"] for record in records),
        "files": records,
        "excluded": [
            "raw/intermediate/processed datasets",
            "historical and last-state checkpoints",
            "periodic epoch checkpoints",
            "Git metadata, caches, credentials and runtime status logs",
            "large historical example artifacts",
        ],
    }
    temporary = ARCHIVE.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for record in records:
            archive.write(REPO / record["path"], f"{PREFIX}/{record['path']}")
        archive.writestr(f"{PREFIX}/PACKAGE_MANIFEST.json",
                         json.dumps(internal, indent=2, sort_keys=True) + "\n")
    temporary.replace(ARCHIVE)
    if ARCHIVE.stat().st_size >= MAX_BYTES:
        ARCHIVE.unlink()
        raise RuntimeError("Submission ZIP exceeds the 95 MB GitHub safety limit")
    external = {
        **{key: value for key, value in internal.items() if key != "files"},
        "archive": ARCHIVE.name,
        "archive_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": sha256_file(ARCHIVE),
        "internal_manifest": f"{PREFIX}/PACKAGE_MANIFEST.json",
    }
    EXTERNAL_MANIFEST.write_text(json.dumps(external, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(external, indent=2))


if __name__ == "__main__":
    main()
