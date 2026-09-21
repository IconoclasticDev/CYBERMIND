#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os

root = Path(r"E:\Cybermind_dataset")
day = "2018-02-16"
expected = 38535667707
etag = "7ef6f23385e8cafe3427e5c612e41eeb-2297"
url = "https://cse-cic-ids2018.s3.ca-central-1.amazonaws.com/Original%20Network%20Traffic%20and%20Log%20data/Friday-16-02-2018/pcap.zip"
part = root / "downloads" / f"{day}_pcap.zip.part"
final = root / "downloads" / f"{day}_pcap.truncated-prefix.bin"
manifest = root / "manifests" / f"{day}.truncated-prefix.json"
status = root / "manifests" / "highspeed_status.json"
window = root / "manifests" / "highspeed_window_final.json"


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temporary, path)


sha = hashlib.sha256()
total = 0
with part.open("rb") as stream:
    while True:
        block = stream.read(8 * 1024 * 1024)
        if not block:
            break
        sha.update(block)
        total += len(block)
if total % (16 * 1024 * 1024):
    raise RuntimeError(f"unaligned committed prefix: {total}")
digest = sha.hexdigest()
os.replace(part, final)
record = {
    "day": day,
    "source_url": url,
    "expected_full_bytes": expected,
    "expected_full_s3_multipart_etag": etag,
    "artifact": str(final),
    "contiguous_prefix": True,
    "byte_zero_included": True,
    "bytes": total,
    "last_fully_written_byte_offset": total - 1,
    "excluded_tail_start_offset": total,
    "excluded_tail_bytes": expected - total,
    "sha256": digest,
    "fraction_of_archive": total / expected,
    "workers": 12,
    "retrieval_order": "consecutive 16 MiB ranges appended strictly in byte order",
    "stop_reason": "observed throughput dropped toward the prior approximately 51 Mbps baseline",
    "finalized_local": datetime.now().astimezone().isoformat(),
    "full_archive_verified": False,
    "s3_multipart_etag_verifiable": False,
    "direct_zip_usability": "not directly extractable until missing tail/central directory is restored",
    "resume_value": "usable as a byte-zero range-resume prefix",
    "export_performed": False,
}
atomic_json(manifest, record)
atomic_json(status, {"state": "finalized_prefix", **record})
atomic_json(window, {
    "state": "stopped_on_speed_drop",
    "completed_verified_days": [],
    "priority_order": ["2018-02-16", "2018-02-15", "2018-02-28", "2018-02-22"],
    "truncated_day": day,
    "truncated_bytes": total,
    "last_fully_written_byte_offset": total - 1,
    "sha256": digest,
    "finished_local": datetime.now().astimezone().isoformat(),
    "export_performed": False,
})
(root / "manifests" / "highspeed_window.lock").unlink(missing_ok=True)
print(json.dumps(record))
