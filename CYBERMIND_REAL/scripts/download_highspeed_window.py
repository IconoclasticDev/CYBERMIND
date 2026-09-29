#!/usr/bin/env python3
"""Time-boxed, ordered PCAP acquisition with atomic per-file publication."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import argparse
import hashlib
import json
import os
import subprocess
import time

MIB = 1024 * 1024
PART = 16 * MIB
ENDPOINT = "https://cse-cic-ids2018.s3.ca-central-1.amazonaws.com/"
SPECS = [
    ("2018-02-16", "Friday-16-02-2018/pcap.zip", 38535667707, "7ef6f23385e8cafe3427e5c612e41eeb-2297"),
    ("2018-02-15", "Thursday-15-02-2018/pcap.zip", 41283382768, "e281e31b104af08f1e670e9bd703ff77-2461"),
    ("2018-02-28", "Wednesday-28-02-2018/pcap.zip", 53251694487, "b688b1c7c529c8754fe11aec1a963270-3175"),
    ("2018-02-22", "Thursday-22-02-2018/pcap.zip", 50240938251, "23f6eb47cd517efd60aa86fea92c5264-2995"),
]


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def url_for(relative: str) -> str:
    return ENDPOINT + quote("Original Network Traffic and Log data/" + relative, safe="/")


def fetch(url: str, start: int, end: int, destination: Path, seconds_left: float) -> dict:
    expected = end - start + 1
    if destination.exists() and destination.stat().st_size == expected:
        return {"complete": True, "bytes": expected, "reused": True, "error": None}
    destination.unlink(missing_ok=True)
    temporary = destination.with_suffix(".tmp")
    temporary.unlink(missing_ok=True)
    max_time = max(10, min(90, int(seconds_left - 10)))
    result = subprocess.run([
        "curl.exe", "--fail", "--location", "--silent", "--show-error",
        "--retry", "1", "--retry-delay", "1", "--retry-all-errors",
        "--connect-timeout", "10", "--max-time", str(max_time),
        "--speed-limit", "16384", "--speed-time", "20",
        "--range", f"{start}-{end}", "--output", str(temporary), url,
    ], capture_output=True, text=True)
    actual = temporary.stat().st_size if temporary.exists() else 0
    if result.returncode == 0 and actual == expected:
        os.replace(temporary, destination)
        return {"complete": True, "bytes": actual, "reused": False, "error": None}
    temporary.unlink(missing_ok=True)
    return {"complete": False, "bytes": actual, "reused": False,
            "error": result.stderr.strip() or f"curl exit {result.returncode}"}


def seed_hashes(path: Path) -> tuple[hashlib._Hash, list[bytes], int]:
    sha = hashlib.sha256()
    md5_parts: list[bytes] = []
    total = 0
    with path.open("rb") as stream:
        while True:
            block = stream.read(PART)
            if not block:
                break
            sha.update(block)
            md5_parts.append(hashlib.md5(block, usedforsecurity=False).digest())
            total += len(block)
    return sha, md5_parts, total


def run_file(root: Path, spec: tuple, workers: int, deadline: datetime, log) -> tuple[str, dict]:
    day, relative, expected, expected_etag = spec
    url = url_for(relative)
    downloads = root / "downloads"
    manifests = root / "manifests"
    batches = root / "intermediate" / "highspeed_ordered" / day
    for directory in (downloads, manifests, batches):
        directory.mkdir(parents=True, exist_ok=True)
    final = downloads / f"{day}_pcap.zip"
    verification = manifests / f"{day}.verification.json"
    prefix = downloads / f"{day}_pcap.truncated-prefix.bin"
    prefix_manifest = manifests / f"{day}.truncated-prefix.json"
    part = downloads / f"{day}_pcap.zip.part"

    if final.exists() and verification.exists():
        record = json.loads(verification.read_text(encoding="utf-8"))
        if record.get("verified") and record.get("bytes") == expected and record.get("s3_multipart_etag") == expected_etag:
            return "complete", record
        raise RuntimeError(f"unsafe existing publication for {day}")

    if prefix.exists() and not part.exists():
        os.replace(prefix, part)
    if part.exists():
        sha, md5_parts, total = seed_hashes(part)
        if total % PART:
            raise RuntimeError(f"{day} prefix is not 16 MiB aligned: {total}")
    else:
        part.touch()
        sha, md5_parts, total = hashlib.sha256(), [], 0
    prefix_manifest.unlink(missing_ok=True)

    network_started = time.monotonic()
    network_start_bytes = total
    last_time, last_bytes = network_started, total
    status_path = manifests / "highspeed_status.json"
    log(f"START {day}: resume={total}; expected={expected}; workers={workers}; ordered 16MiB ranges")

    with part.open("ab") as output:
        while total < expected:
            seconds_left = (deadline - datetime.now().astimezone()).total_seconds()
            if seconds_left <= 20:
                break
            first_index = total // PART
            jobs = []
            for offset in range(workers):
                start = (first_index + offset) * PART
                if start >= expected:
                    break
                end = min(expected, start + PART) - 1
                destination = batches / f"{first_index + offset:05d}.range"
                jobs.append((start, end, destination))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = list(pool.map(lambda job: fetch(url, *job, seconds_left), jobs))

            appended = 0
            first_error = None
            for (start, end, destination), result in zip(jobs, results):
                if not result["complete"]:
                    first_error = result["error"]
                    break
                block = destination.read_bytes()
                output.write(block)
                sha.update(block)
                md5_parts.append(hashlib.md5(block, usedforsecurity=False).digest())
                total += len(block)
                appended += len(block)
                destination.unlink(missing_ok=True)
            output.flush()
            os.fsync(output.fileno())
            now = time.monotonic()
            interval = max(now - last_time, 1e-6)
            interval_rate = (total - last_bytes) / interval
            overall_rate = (total - network_start_bytes) / max(now - network_started, 1e-6)
            state = {
                "state": "downloading", "day": day, "bytes": total, "expected_bytes": expected,
                "fraction": total / expected, "last_fully_written_byte_offset": total - 1,
                "workers": workers, "retrieval_order": "consecutive ranges appended strictly in byte order",
                "interval_bytes_per_second": interval_rate, "overall_bytes_per_second": overall_rate,
                "deadline_local": deadline.isoformat(), "updated_local": datetime.now().astimezone().isoformat(),
                "first_error": first_error,
            }
            atomic_json(status_path, state)
            log(f"PROGRESS {day}: {total}/{expected} ({total/expected:.2%}); interval={interval_rate/MIB:.2f} MiB/s; overall={overall_rate/MIB:.2f} MiB/s")
            last_time, last_bytes = now, total
            if appended == 0:
                time.sleep(1)

    if total == expected:
        output_etag = hashlib.md5(b"".join(md5_parts), usedforsecurity=False).hexdigest() + f"-{len(md5_parts)}"
        if output_etag != expected_etag:
            raise RuntimeError(f"{day} ETag mismatch: {output_etag} != {expected_etag}")
        digest = sha.hexdigest()
        os.replace(part, final)
        record = {
            "day": day, "source_url": url, "bytes": total, "sha256": digest,
            "s3_multipart_etag": output_etag, "expected_s3_multipart_etag": expected_etag,
            "s3_part_size": PART, "workers": workers, "atomic_publication": True,
            "verified": True, "published_path": str(final),
            "completed_at_utc": datetime.now(timezone.utc).isoformat(), "export_performed": False,
        }
        atomic_json(verification, record)
        atomic_json(status_path, {"state": "verified", **record})
        log(f"COMPLETE {day}: sha256={digest}; etag={output_etag}")
        return "complete", record

    digest = sha.hexdigest()
    truncated = downloads / f"{day}_pcap.truncated-prefix.bin"
    os.replace(part, truncated)
    record = {
        "day": day, "source_url": url, "expected_full_bytes": expected,
        "expected_full_s3_multipart_etag": expected_etag, "artifact": str(truncated),
        "contiguous_prefix": True, "byte_zero_included": True, "bytes": total,
        "last_fully_written_byte_offset": total - 1, "excluded_tail_start_offset": total,
        "excluded_tail_bytes": expected - total, "sha256": digest,
        "fraction_of_archive": total / expected, "workers": workers,
        "retrieval_order": "consecutive ranges appended strictly in byte order",
        "finalized_local": datetime.now().astimezone().isoformat(),
        "full_archive_verified": False, "s3_multipart_etag_verifiable": False,
        "direct_zip_usability": "not directly extractable until missing tail/central directory is restored",
        "resume_value": "usable as a byte-zero range-resume prefix", "export_performed": False,
    }
    atomic_json(prefix_manifest, record)
    atomic_json(status_path, {"state": "finalized_prefix", **record})
    log(f"PREFIX {day}: bytes={total}; last_offset={total-1}; sha256={digest}")
    return "prefix", record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(r"E:\Cybermind_dataset"))
    parser.add_argument("--workers", type=int, choices=range(10, 13), default=12)
    parser.add_argument("--deadline", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if root.drive.upper() != "E:":
        raise ValueError("high-speed acquisition is pinned to E:")
    deadline = datetime.fromisoformat(args.deadline)
    if deadline.tzinfo is None:
        deadline = deadline.astimezone()
    logs = root / "logs"
    manifests = root / "manifests"
    logs.mkdir(parents=True, exist_ok=True)
    manifests.mkdir(parents=True, exist_ok=True)
    log_path = logs / "highspeed_window.log"

    def log(message: str) -> None:
        line = f"{datetime.now().astimezone().isoformat()} {message}"
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
        print(line, flush=True)

    lock = manifests / "highspeed_window.lock"
    handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(handle, json.dumps({"pid": os.getpid(), "deadline": deadline.isoformat()}).encode())
        os.close(handle)
        completed = []
        for spec in SPECS:
            if (deadline - datetime.now().astimezone()).total_seconds() <= 20:
                break
            result, record = run_file(root, spec, args.workers, deadline, log)
            if result == "complete":
                completed.append(record["day"])
                continue
            break
        atomic_json(manifests / "highspeed_window_final.json", {
            "state": "stopped_at_deadline", "deadline_local": deadline.isoformat(),
            "completed_verified_days": completed, "priority_order": [row[0] for row in SPECS],
            "finished_local": datetime.now().astimezone().isoformat(), "export_performed": False,
        })
        log(f"WINDOW END: completed={completed}")
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
