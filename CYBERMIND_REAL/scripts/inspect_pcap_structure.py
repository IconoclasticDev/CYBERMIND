"""Read-only structural audit for classic Ethernet PCAP records.

Reports malformed/truncated IPv4 records without changing or excluding source data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import ipaddress


def inspect(path: Path, stop_after: int | None = None) -> dict:
    findings: list[dict] = []
    records = 0
    with path.open("rb") as handle:
        global_header = handle.read(24)
        if len(global_header) != 24 or global_header[:4] not in (
            b"\xd4\xc3\xb2\xa1",
            b"\xa1\xb2\xc3\xd4",
        ):
            raise ValueError("Expected classic microsecond PCAP")
        order = "<" if global_header[:4] == b"\xd4\xc3\xb2\xa1" else ">"
        snaplen = struct.unpack_from(order + "I", global_header, 16)[0]
        linktype = struct.unpack_from(order + "I", global_header, 20)[0]
        while True:
            record_offset = handle.tell()
            record_header = handle.read(16)
            if not record_header:
                break
            records += 1
            if len(record_header) != 16:
                findings.append({"record": records, "record_offset": record_offset,
                                 "kind": "truncated_record_header",
                                 "available": len(record_header), "required": 16})
                break
            seconds, micros, captured_len, wire_len = struct.unpack(order + "4I", record_header)
            raw = handle.read(captured_len)
            if len(raw) != captured_len:
                findings.append({"record": records, "record_offset": record_offset,
                                 "kind": "truncated_record_payload",
                                 "available": len(raw), "declared": captured_len})
                break
            if len(raw) >= 14:
                ethernet_offset = 14
                ether_type = struct.unpack_from("!H", raw, 12)[0]
                while ether_type in (0x8100, 0x88A8) and len(raw) >= ethernet_offset + 4:
                    ether_type = struct.unpack_from("!H", raw, ethernet_offset + 2)[0]
                    ethernet_offset += 4
                if ether_type == 0x0800:
                    ip = raw[ethernet_offset:]
                    if len(ip) < 20:
                        kind = "truncated_ipv4_header"
                        details = {"ip_bytes_available": len(ip)}
                    else:
                        version = ip[0] >> 4
                        ihl = (ip[0] & 15) * 4
                        ip_total_len = struct.unpack_from("!H", ip, 2)[0]
                        kind = None
                        details = {"ip_version": version, "ip_header_len": ihl,
                                   "ip_total_len": ip_total_len,
                                   "ip_bytes_available": len(ip),
                                   "missing_ip_bytes": max(0, ip_total_len - len(ip))}
                        if version == 4 and ihl >= 20 and len(ip) >= ihl:
                            details.update(
                                protocol=ip[9],
                                source_ip=str(ipaddress.IPv4Address(ip[12:16])),
                                destination_ip=str(ipaddress.IPv4Address(ip[16:20])),
                            )
                            transport = ip[ihl:]
                            if ip[9] == 6 and len(transport) >= 20:
                                details.update(
                                    source_port=struct.unpack_from("!H", transport, 0)[0],
                                    destination_port=struct.unpack_from("!H", transport, 2)[0],
                                    tcp_header_len=(transport[12] >> 4) * 4,
                                )
                            elif ip[9] == 17 and len(transport) >= 8:
                                details.update(
                                    source_port=struct.unpack_from("!H", transport, 0)[0],
                                    destination_port=struct.unpack_from("!H", transport, 2)[0],
                                    udp_length=struct.unpack_from("!H", transport, 4)[0],
                                )
                        if version != 4:
                            kind = "invalid_ipv4_version"
                        elif ihl < 20:
                            kind = "invalid_ipv4_ihl"
                        elif ip_total_len < ihl:
                            kind = "invalid_ipv4_total_len"
                        elif len(ip) < ip_total_len:
                            kind = "capture_truncated_ipv4_payload"
                    if kind:
                        findings.append({"record": records, "record_offset": record_offset,
                                         "timestamp_epoch": seconds + micros / 1_000_000,
                                         "captured_len": captured_len, "wire_len": wire_len,
                                         "snaplen": snaplen, "kind": kind, **details})
            if stop_after is not None and records >= stop_after:
                break
    return {"source": str(path), "snaplen": snaplen, "linktype": linktype,
            "records_scanned": records, "findings": findings}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("--stop-after", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect(args.capture, args.stop_after)
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
