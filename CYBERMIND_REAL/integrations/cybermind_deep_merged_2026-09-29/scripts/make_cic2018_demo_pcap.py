"""Extract a bounded, packet-faithful CIC-IDS2018 demo interval from a verified ZIP.

The manifest records the corrected-label interval used to select the window.
It does not assign ground truth to individual packets or model predictions.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import zipfile


MEMBER = "pcap/capEC2AMAZ-O4EL3NG-172.31.69.24-part2"
START = 1519829000.0
END = 1519829900.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("verification", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    verified = json.loads(args.verification.read_text(encoding="utf-8"))
    if not verified.get("verified") or verified.get("bytes") != args.archive.stat().st_size:
        raise SystemExit("Source archive has no matching verified size manifest")
    if verified.get("s3_multipart_etag") != verified.get("expected_s3_multipart_etag"):
        raise SystemExit("Source archive ETag mismatch")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_name(args.output.name + ".partial")
    hasher = hashlib.sha256()
    count = 0
    first = last = None
    with zipfile.ZipFile(args.archive) as archive:
        info = archive.getinfo(MEMBER)
        with archive.open(info) as source, temp.open("wb") as output:
            header = source.read(24)
            if len(header) != 24:
                raise ValueError("Incomplete pcap header")
            magic = header[:4]
            if magic == b"\xd4\xc3\xb2\xa1":
                endian, precision = "<", 1_000_000
            elif magic == b"\x4d\x3c\xb2\xa1":
                endian, precision = "<", 1_000_000_000
            elif magic == b"\xa1\xb2\xc3\xd4":
                endian, precision = ">", 1_000_000
            elif magic == b"\xa1\xb2\x3c\x4d":
                endian, precision = ">", 1_000_000_000
            else:
                raise ValueError(f"Unsupported pcap magic: {magic.hex()}")
            output.write(header)
            hasher.update(header)
            while True:
                record_header = source.read(16)
                if not record_header:
                    break
                if len(record_header) != 16:
                    raise ValueError("Incomplete pcap record header")
                seconds, fractional, caplen, _ = struct.unpack(endian + "IIII", record_header)
                if caplen > 10_000_000:
                    raise ValueError(f"Implausible captured packet length: {caplen}")
                packet = source.read(caplen)
                if len(packet) != caplen:
                    raise ValueError("Incomplete captured packet")
                timestamp = seconds + fractional / precision
                if timestamp > END:
                    break
                if timestamp < START:
                    continue
                output.write(record_header)
                output.write(packet)
                hasher.update(record_header)
                hasher.update(packet)
                count += 1
                first = timestamp if first is None else first
                last = timestamp
    if count < 100:
        raise ValueError(f"Only {count} packets in selected interval")
    temp.replace(args.output)
    manifest = {
        "source_dataset": "CSE-CIC-IDS2018",
        "archive": str(args.archive),
        "archive_sha256": verified["sha256"],
        "archive_s3_multipart_etag": verified["s3_multipart_etag"],
        "archive_member": MEMBER,
        "archive_member_crc32": f"{info.CRC:08x}",
        "selection_start_utc": datetime.fromtimestamp(START, timezone.utc).isoformat(),
        "selection_end_utc": datetime.fromtimestamp(END, timezone.utc).isoformat(),
        "selection_basis": "Preidentified Feb 28 victim-host interval containing corrected D_0228_INF_NMAP and D_0228_INF_COMM rules; raw packets retain no per-packet ground-truth labels.",
        "corrected_label_source": "Distrinet CNS2022 corrected CSE-CIC-IDS2018 rules, commit f0ce502818e59e6cd062720ab2286c5ff6f2bdec",
        "first_packet_utc": datetime.fromtimestamp(first, timezone.utc).isoformat(),
        "last_packet_utc": datetime.fromtimestamp(last, timezone.utc).isoformat(),
        "packet_count": count,
        "output": str(args.output),
        "output_bytes": args.output.stat().st_size,
        "output_sha256": hasher.hexdigest(),
        "limitations": "A selected known-attack interval is a functional demonstration, not held-out accuracy or proof of generalization. The raw-PCAP import does not carry corrected flow labels.",
    }
    manifest_path = args.output.with_suffix(args.output.suffix + ".provenance.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
