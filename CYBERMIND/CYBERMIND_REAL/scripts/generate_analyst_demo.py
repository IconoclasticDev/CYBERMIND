"""Generate small, deterministic, unlabeled PCAPs for UI walkthroughs."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from scapy.all import IP, TCP, Raw, wrpcap

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "examples" / "analyst_demo"
START = 1700000000

def packet(src, dst, sport, dport, tick, payload):
    value = IP(src=src, dst=dst) / TCP(sport=sport, dport=dport, flags="PA", seq=1) / Raw(load=payload)
    value.time = START + tick
    return value

def build():
    DEST.mkdir(parents=True, exist_ok=True)
    web, probe = [], []
    for index in range(24):
        for offset, port in enumerate((80, 443)):
            web.append(packet("10.42.0.10", "198.51.100.20", 42000 + index * 2 + offset,
                              port, index * 30 + offset, b"GET /demo HTTP/1.1\r\n\r\n"))
        for offset in range(6):
            probe.append(packet("10.42.0.25", "10.42.0.50", 43000 + index * 6 + offset,
                                2000 + index * 6 + offset, index * 30 + offset,
                                b"CYBERMIND SYNTHETIC DEMO"))
    manifest = []
    for filename, packets, title, description in [
        ("web_like.pcap", web, "Web-like flow",
         "Synthetic repeated HTTP/HTTPS-style connections between two hosts."),
        ("sequential_ports.pcap", probe, "Sequential ports",
         "Synthetic sequential destination-port traffic for flow review."),
    ]:
        path = DEST / filename
        wrpcap(str(path), packets)
        manifest.append({"id": path.stem, "file": filename, "title": title,
                         "description": description, "synthetic": True,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "bytes": path.stat().st_size})
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    build()

