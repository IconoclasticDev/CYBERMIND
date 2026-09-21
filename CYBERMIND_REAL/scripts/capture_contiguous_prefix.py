#!/usr/bin/env python3
"""Build a byte-zero CIC-IDS2018 archive prefix and finalize it before a cutoff."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time

MIB = 1024 * 1024
EXPECTED_BYTES = 53251694487
EXPECTED_ETAG = "b688b1c7c529c8754fe11aec1a963270-3175"
URL = "https://cse-cic-ids2018.s3.ca-central-1.amazonaws.com/Original%20Network%20Traffic%20and%20Log%20data/Wednesday-28-02-2018/pcap.zip"


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def fetch(url, start, end, destination, max_time):
    temporary = destination.with_suffix(".tmp")
    temporary.unlink(missing_ok=True)
    result = subprocess.run([
        "curl.exe", "--fail", "--location", "--silent", "--show-error",
        "--retry", "4", "--retry-delay", "1", "--retry-all-errors",
        "--connect-timeout", "20", "--max-time", str(max(1, int(max_time))),
        "--range", f"{start}-{end}", "--output", str(temporary), url,
    ], capture_output=True, text=True)
    expected = end - start + 1
    actual = temporary.stat().st_size if temporary.exists() else 0
    if result.returncode == 0 and actual == expected:
        os.replace(temporary, destination)
        return {"complete": True, "bytes": actual, "error": None}
    return {"complete": False, "bytes": actual,
            "error": result.stderr.strip() or f"curl exit {result.returncode}"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(r"E:\Cybermind_dataset"))
    parser.add_argument("--cutoff", required=True, help="Local ISO timestamp")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--source-segments", type=Path,
                        default=Path(r"E:\Cybermind_dataset\intermediate\download_segments\2018-02-28"))
    args = parser.parse_args()
    root = args.root.resolve()
    if root.drive.upper() != "E:" or args.workers != 6:
        raise ValueError("This cutoff run is pinned to E: and exactly six ordered workers")
    cutoff = datetime.fromisoformat(args.cutoff)
    if cutoff.tzinfo is not None:
        cutoff = cutoff.astimezone().replace(tzinfo=None)

    downloads = root / "downloads"
    manifests = root / "manifests"
    batches = root / "intermediate" / "contiguous_batch"
    logs = root / "logs"
    for directory in (downloads, manifests, batches, logs):
        directory.mkdir(parents=True, exist_ok=True)
    part = downloads / "2018-02-28_pcap.truncated-prefix.part"
    final = downloads / "2018-02-28_pcap.truncated-prefix.bin"
    status_path = manifests / "contiguous_prefix_status.json"
    manifest_path = manifests / "2018-02-28.truncated-prefix.json"
    log_path = logs / "contiguous_prefix.log"

    def log(message):
        line = f"{datetime.now().astimezone().isoformat()} {message}"
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
        print(line, flush=True)

    sha = hashlib.sha256()
    total = 0
    reused_segments = 0
    started = time.monotonic()
    last_sample_time = started
    last_sample_bytes = 0
    segment_size = 64 * MIB
    range_size = 16 * MIB

    part.unlink(missing_ok=True)
    final.unlink(missing_ok=True)
    with part.open("wb") as output:
        # Reuse only the exact, gap-free byte-zero prefix from the earlier range run.
        index = 0
        while True:
            source = args.source_segments / f"{index:05d}.seg"
            if not source.exists() or source.stat().st_size != segment_size:
                break
            with source.open("rb") as stream:
                while True:
                    block = stream.read(4 * MIB)
                    if not block:
                        break
                    output.write(block)
                    sha.update(block)
                    total += len(block)
            reused_segments += 1
            index += 1
        output.flush()
        os.fsync(output.fileno())
        log(f"PREFIX REUSED: {total} contiguous bytes from {reused_segments} verified ranges")
        last_sample_time = time.monotonic()
        last_sample_bytes = total

        range_index = total // range_size
        while total < EXPECTED_BYTES:
            seconds_left = (cutoff - datetime.now()).total_seconds()
            if seconds_left <= 10:
                break
            jobs = []
            for offset in range(args.workers):
                start = (range_index + offset) * range_size
                if start >= EXPECTED_BYTES:
                    break
                end = min(EXPECTED_BYTES, start + range_size) - 1
                destination = batches / f"{range_index + offset:05d}.range"
                jobs.append((range_index + offset, start, end, destination))
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = [pool.submit(fetch, URL, start, end, destination, min(600, seconds_left - 5))
                           for _, start, end, destination in jobs]
                outcomes = [future.result() for future in futures]
            appended = 0
            for (idx, start, end, destination), outcome in zip(jobs, outcomes):
                if not outcome["complete"]:
                    log(f"CUTOFF/INCOMPLETE range {start}-{end}: {outcome['error']}")
                    break
                with destination.open("rb") as stream:
                    while True:
                        block = stream.read(4 * MIB)
                        if not block:
                            break
                        output.write(block)
                        sha.update(block)
                        total += len(block)
                        appended += len(block)
                destination.unlink(missing_ok=True)
                range_index = idx + 1
            output.flush()
            os.fsync(output.fileno())
            now = time.monotonic()
            interval = max(now - last_sample_time, 1e-6)
            sustained = (total - last_sample_bytes) / interval
            overall = total / max(now - started, 1e-6)
            status = {
                "state": "downloading_contiguous_prefix", "day": "2018-02-28",
                "bytes": total, "expected_bytes": EXPECTED_BYTES, "fraction": total / EXPECTED_BYTES,
                "last_fully_written_byte_offset": total - 1 if total else None,
                "workers": args.workers, "retrieval_order": "byte-zero contiguous; ordered six-range batches",
                "interval_bytes_per_second": sustained, "overall_bytes_per_second": overall,
                "cutoff_local": cutoff.astimezone().isoformat(), "updated_local": datetime.now().astimezone().isoformat(),
            }
            atomic_json(status_path, status)
            log(f"PROGRESS: {total}/{EXPECTED_BYTES} ({total/EXPECTED_BYTES:.2%}); {sustained/MIB:.2f} MiB/s interval")
            last_sample_time, last_sample_bytes = now, total
            if appended < sum(end - start + 1 for _, start, end, _ in jobs):
                break

        output.flush()
        os.fsync(output.fileno())

    digest = sha.hexdigest()
    os.replace(part, final)
    fraction = total / EXPECTED_BYTES
    manifest = {
        "day": "2018-02-28", "source_url": URL, "expected_full_bytes": EXPECTED_BYTES,
        "expected_full_s3_multipart_etag": EXPECTED_ETAG, "artifact": str(final),
        "contiguous_prefix": True, "byte_zero_included": True, "bytes": total,
        "last_fully_written_byte_offset": total - 1 if total else None,
        "excluded_tail_start_offset": total, "excluded_tail_bytes": EXPECTED_BYTES - total,
        "sha256": digest, "fraction_of_archive": fraction, "workers": args.workers,
        "retrieval_order": "ordered six-range batches appended strictly in byte order",
        "reused_gap_free_64mib_segments": reused_segments,
        "cutoff_local": cutoff.astimezone().isoformat(), "finalized_local": datetime.now().astimezone().isoformat(),
        "full_archive_verified": False, "s3_multipart_etag_verifiable": False,
        "direct_zip_usability": "not directly extractable until missing tail/central directory is restored",
        "resume_value": "usable as a byte-zero range-resume prefix for completing the official object",
        "export_performed": False,
    }
    atomic_json(manifest_path, manifest)
    atomic_json(status_path, {"state": "finalized", **manifest})
    log(f"FINALIZED: bytes={total}; last_offset={total-1}; sha256={digest}")


if __name__ == "__main__":
    main()
