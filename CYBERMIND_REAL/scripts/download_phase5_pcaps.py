#!/usr/bin/env python3
"""Sequential, resumable, atomically published CIC-IDS2018 PCAP acquisition."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import threading
import time

ENDPOINT = "https://cse-cic-ids2018.s3.ca-central-1.amazonaws.com/"
MIB = 1024 * 1024
GIB = 1024 * MIB
S3_PART_SIZE = 16 * MIB

SPECS = [
    ("2018-02-28", "Wednesday-28-02-2018/pcap.zip", 53251694487, "b688b1c7c529c8754fe11aec1a963270-3175"),
    ("2018-02-16", "Friday-16-02-2018/pcap.zip", 38535667707, "7ef6f23385e8cafe3427e5c612e41eeb-2297"),
    ("2018-02-15", "Thursday-15-02-2018/pcap.zip", 41283382768, "e281e31b104af08f1e670e9bd703ff77-2461"),
    ("2018-02-22", "Thursday-22-02-2018/pcap.zip", 50240938251, "23f6eb47cd517efd60aa86fea92c5264-2995"),
    ("2018-02-20", "Tuesday-20-02-2018/pcap.rar", 44391980380, "8aa242e62fde4eaa43d1ad66d545a213-2646"),
    ("2018-02-21", "Wednesday-21-02-2018/pcap.zip", 53462820707, "d8e019df7ae51d9fefb558f57cdfb5f9-3187"),
    ("2018-02-23", "Friday-23-02-2018/pcap.zip", 59093922810, "a39a7470586d7fd0930431980a5b0c31-3523"),
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Recorder:
    def __init__(self, root: Path):
        self.root = root
        self.logs = root / "logs"
        self.manifests = root / "manifests"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.manifests.mkdir(parents=True, exist_ok=True)
        self.log_path = self.logs / "phase5_download.log"
        self.status_path = self.manifests / "download_status.json"
        self.lock = threading.Lock()

    def log(self, message):
        line = f"{utc_now()} {message}"
        with self.lock:
            with self.log_path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
        print(line, flush=True)

    def status(self, payload):
        payload = {"updated_at_utc": utc_now(), **payload}
        temporary = self.status_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temporary, self.status_path)


def object_url(relative):
    from urllib.parse import quote
    key = "Original Network Traffic and Log data/" + relative
    return ENDPOINT + quote(key, safe="/")


def remote_check(url, expected_size, expected_etag):
    result = subprocess.run(
        ["curl.exe", "--head", "--fail", "--silent", "--show-error", "--max-time", "60", url],
        check=True, capture_output=True, text=True,
    )
    headers = {}
    for line in result.stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    size = int(headers["content-length"])
    etag = headers.get("etag", "").strip('"').lower()
    modified = headers.get("last-modified")
    if size != expected_size or etag != expected_etag:
        raise RuntimeError(f"Remote identity mismatch: size={size}, etag={etag}")
    return {"content_length": size, "etag": etag, "last_modified": modified}


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def load_or_create_state(path, identity, segment_size):
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        required = {"url": identity["url"], "size": identity["size"], "etag": identity["etag"], "segment_size": segment_size}
        if any(state.get(key) != value for key, value in required.items()):
            raise RuntimeError("Resume-state identity differs from requested object")
        return state
    state = {
        "version": 1, "url": identity["url"], "size": identity["size"],
        "etag": identity["etag"], "segment_size": segment_size,
        "completed_segments": [], "created_at_utc": utc_now(),
    }
    atomic_json(path, state)
    return state


def download_range(url, segment_path, start, end):
    expected = end - start + 1
    temporary = segment_path.with_suffix(".tmp")
    temporary.unlink(missing_ok=True)
    result = subprocess.run([
        "curl.exe", "--fail", "--location", "--silent", "--show-error",
        "--retry", "8", "--retry-delay", "2", "--retry-all-errors",
        "--connect-timeout", "30", "--max-time", "900",
        "--range", f"{start}-{end}", "--output", str(temporary), url,
    ], capture_output=True, text=True)
    if result.returncode != 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"curl range {start}-{end} failed: {result.stderr.strip()}")
    actual = temporary.stat().st_size
    if actual != expected:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Range {start}-{end} length mismatch: {actual}/{expected}")
    os.replace(temporary, segment_path)
    return expected


def assemble_and_verify(segment_dir, segment_count, part_path, expected_size, expected_etag, recorder, day):
    sha = hashlib.sha256()
    part_digests = []
    read_bytes = 0
    last_status = 0.0
    with part_path.open("wb") as output:
        for index in range(segment_count):
            segment_path = segment_dir / f"{index:05d}.seg"
            with segment_path.open("rb") as stream:
                while True:
                    block = stream.read(S3_PART_SIZE)
                    if not block:
                        break
                    output.write(block)
                    sha.update(block)
                    part_digests.append(hashlib.md5(block, usedforsecurity=False).digest())
                    read_bytes += len(block)
                    now = time.monotonic()
                    if now - last_status >= 60:
                        recorder.status({"state": "verifying", "day": day, "verified_bytes": read_bytes,
                                         "expected_bytes": expected_size, "progress": read_bytes / expected_size})
                        last_status = now
        output.flush()
        os.fsync(output.fileno())
    if read_bytes != expected_size or part_path.stat().st_size != expected_size:
        raise RuntimeError(f"Assembled size mismatch: {read_bytes}/{expected_size}")
    local_etag = hashlib.md5(b"".join(part_digests), usedforsecurity=False).hexdigest() + f"-{len(part_digests)}"
    if local_etag != expected_etag:
        raise RuntimeError(f"S3 multipart ETag mismatch: {local_etag} != {expected_etag}")
    return sha.hexdigest(), local_etag


def completed_records(manifests):
    records = []
    for path in sorted(manifests.glob("2018-*.verification.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("verified") is True:
            records.append(record)
    return records


def acquire(spec, root, recorder, workers, segment_size):
    day, relative, expected_size, expected_etag = spec
    suffix = Path(relative).suffix
    downloads = root / "downloads"
    intermediate = root / "intermediate" / "download_segments"
    downloads.mkdir(parents=True, exist_ok=True)
    intermediate.mkdir(parents=True, exist_ok=True)
    final_path = downloads / f"{day}_pcap{suffix}"
    part_path = downloads / f"{day}_pcap{suffix}.part"
    segment_dir = intermediate / day
    segment_dir.mkdir(parents=True, exist_ok=True)
    state_path = segment_dir / "identity.json"
    verification_path = recorder.manifests / f"{day}.verification.json"
    url = object_url(relative)

    if verification_path.exists() and final_path.exists():
        prior = json.loads(verification_path.read_text(encoding="utf-8"))
        if prior.get("verified") and prior.get("bytes") == expected_size and prior.get("s3_multipart_etag") == expected_etag:
            recorder.log(f"SKIP {day}: previously verified archive is present")
            return prior
        raise RuntimeError(f"Existing publication for {day} is not safely reusable")

    remote = remote_check(url, expected_size, expected_etag)
    free = shutil.disk_usage(root).free
    if free < expected_size + 20 * GIB:
        raise RuntimeError(f"Insufficient free space for {day}: {free} bytes")
    identity = {"url": url, "size": expected_size, "etag": expected_etag}
    state = load_or_create_state(state_path, identity, segment_size)
    part_path.unlink(missing_ok=True)

    segment_count = math.ceil(expected_size / segment_size)
    completed = set()
    for index in range(segment_count):
        path = segment_dir / f"{index:05d}.seg"
        expected = min(segment_size, expected_size - index * segment_size)
        if path.exists() and path.stat().st_size == expected:
            completed.add(index)
        elif path.exists():
            path.unlink()
    ranges = [(index, index * segment_size, min(expected_size, (index + 1) * segment_size) - 1)
              for index in range(segment_count) if index not in completed]
    completed_bytes = sum(min(segment_size, expected_size - index * segment_size) for index in completed)
    start_time = time.monotonic()
    start_bytes = completed_bytes
    recorder.log(f"START {day}: {expected_size} bytes; {workers} concurrent ranges; {len(completed)}/{segment_count} resumed")

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix=f"pcap-{day}") as pool:
        pending = {pool.submit(download_range, url, segment_dir / f"{index:05d}.seg", start, end): (index, start, end)
                   for index, start, end in ranges}
        last_report = 0.0
        while pending:
            done, _ = wait(pending, timeout=5, return_when=FIRST_COMPLETED)
            for future in done:
                index, start, end = pending.pop(future)
                completed_bytes += future.result()
                completed.add(index)
            now = time.monotonic()
            if now - last_report >= 60 or not pending:
                elapsed = max(now - start_time, 1e-6)
                speed = max(completed_bytes - start_bytes, 0) / elapsed
                remaining = expected_size - completed_bytes
                status = {
                    "state": "downloading", "day": day, "priority_order": [row[0] for row in SPECS],
                    "completed_days": [row["day"] for row in completed_records(recorder.manifests)],
                    "downloaded_bytes": completed_bytes, "expected_bytes": expected_size,
                    "progress": completed_bytes / expected_size, "bytes_per_second": speed,
                    "eta_seconds": remaining / speed if speed else None, "workers": workers,
                    "partial_path": str(segment_dir), "final_path": str(final_path),
                }
                recorder.status(status)
                recorder.log(f"PROGRESS {day}: {status['progress']:.2%}; {speed / MIB:.2f} MiB/s")
                last_report = now
    recorder.log(f"VERIFY {day}: all ranges complete; assembling and computing SHA-256/S3 multipart ETag")
    recorder.status({"state": "verifying", "day": day, "verified_bytes": 0,
                     "expected_bytes": expected_size, "progress": 0.0})
    sha256, local_etag = assemble_and_verify(segment_dir, segment_count, part_path, expected_size,
                                             expected_etag, recorder, day)
    os.replace(part_path, final_path)
    record = {
        "day": day, "source_url": url, "source_key": "Original Network Traffic and Log data/" + relative,
        "bytes": expected_size, "sha256": sha256, "s3_multipart_etag": local_etag,
        "s3_part_size": S3_PART_SIZE, "remote_last_modified": remote["last_modified"],
        "workers": workers, "atomic_publication": True, "verified": True,
        "published_path": str(final_path), "completed_at_utc": utc_now(),
        "export_performed": False,
    }
    atomic_json(verification_path, record)
    shutil.rmtree(segment_dir)
    recorder.log(f"COMPLETE {day}: sha256={sha256}; etag={local_etag}")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(r"E:\Cybermind_dataset"))
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--segment-mib", type=int, default=64)
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 32 or args.segment_mib < 16:
        raise ValueError("workers must be 1..32 and segment-mib must be at least 16")
    root = args.root.resolve()
    if root.drive.upper() != "E:":
        raise ValueError(f"Phase 5 acquisition is pinned to E:, got {root}")
    root.mkdir(parents=True, exist_ok=True)
    recorder = Recorder(root)
    lock_path = recorder.manifests / "phase5_download.lock"
    try:
        handle = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise RuntimeError("Another Phase 5 downloader may already be active") from error
    try:
        os.write(handle, json.dumps({"pid": os.getpid(), "started_at_utc": utc_now()}).encode())
        os.close(handle)
        recorder.log("SESSION START: sequential raw-PCAP acquisition; exporter disabled")
        for spec in SPECS:
            acquire(spec, root, recorder, args.workers, args.segment_mib * MIB)
        records = completed_records(recorder.manifests)
        recorder.status({"state": "complete", "completed_days": [row["day"] for row in records],
                         "completed_count": len(records), "requested_count": len(SPECS)})
        recorder.log(f"SESSION COMPLETE: {len(records)}/{len(SPECS)} days verified")
    except BaseException as error:
        records = completed_records(recorder.manifests)
        recorder.status({"state": "failed", "error": repr(error),
                         "completed_days": [row["day"] for row in records],
                         "completed_count": len(records), "requested_count": len(SPECS)})
        recorder.log(f"SESSION FAILED: {error!r}")
        raise
    finally:
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
