from __future__ import annotations

import csv
import io
import json
from collections import deque
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel, Field, ValidationError

from app.core.logging import log


class TelemetryEvent(BaseModel):
    """Unified event schema (data/manifests/schema.json subset)."""

    timestamp: float | str
    src: str
    dst: str
    label: str = "BENIGN"
    source: str = "api"
    src_port: float | None = None
    dst_port: float | None = None
    protocol: float | str | None = None
    bytes_fwd: float = 0.0
    bytes_bwd: float = 0.0
    packets_fwd: float = 0.0
    packets_bwd: float = 0.0
    duration: float = 0.0
    mean_fwd_iat: float = 0.0
    mean_bwd_iat: float = 0.0
    flow_bytes_s: float = 0.0
    flow_packets_s: float = 0.0
    attack_stage: int | None = Field(default=None, ge=0, le=6)
    technique_id: str | None = None
    vulnerability_context: str | None = None
    source_file: str | None = None
    scenario_id: str | None = None
    provenance: str | None = None
    ttl_mean: float = 0.0
    ttl_variance: float = 0.0
    tcp_window_mean: float = 0.0
    tcp_window_variance: float = 0.0
    ip_df_ratio: float = 0.0
    ip_mf_ratio: float = 0.0
    ip_fragment_ratio: float = 0.0
    payload_size_mean: float = 0.0
    payload_size_variance: float = 0.0
    payload_size_min: float = 0.0
    payload_size_max: float = 0.0
    payload_size_p25: float = 0.0
    payload_size_p50: float = 0.0
    payload_size_p75: float = 0.0
    scan_unique_ports: float = 0.0
    scan_sequential_score: float = 0.0
    scan_randomized_score: float = 0.0
    retransmission_count: float = 0.0
    retransmission_ratio: float = 0.0
    packet_features_available: float = 0.0

    model_config = {"extra": "ignore"}


def _ensure_provenance(e: TelemetryEvent) -> TelemetryEvent:
    if not e.provenance:
        object.__setattr__(e, "provenance", f"ingest:{e.source}:{e.timestamp}")
    return e


class TelemetryService:
    """In-memory bounded event buffer with replay/file ingestion."""

    def __init__(self, buffer_size: int = 20000) -> None:
        self.events: deque[dict[str, Any]] = deque(maxlen=buffer_size)
        self.dropped = 0

    def ingest(self, events: list[TelemetryEvent]) -> int:
        accepted = 0
        for e in events:
            try:
                rec = _ensure_provenance(e).model_dump()
            except ValidationError:
                self.dropped += 1
                continue
            self.events.append(rec)
            accepted += 1
        return accepted

    def ingest_raw(self, raw: list[dict[str, Any]], source: str) -> tuple[int, int]:
        """Bulk ingest with per-item validation; returns (accepted, rejected)."""
        accepted = rejected = 0
        for item in raw:
            if not isinstance(item, dict):
                rejected += 1
                continue
            item = {**item, "source": item.get("source") or source}
            try:
                e = TelemetryEvent(**item)
            except ValidationError as exc:
                log.debug("telemetry rejected: %s", exc.errors()[:1])
                rejected += 1
                continue
            self.events.append(_ensure_provenance(e).model_dump())
            accepted += 1
        return accepted, rejected

    def latest(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(self.events)[-limit:]

    def __len__(self) -> int:
        return len(self.events)

    # ------------------------------------------------------------- ingestion
    @staticmethod
    def parse_jsonl(text: str) -> Iterator[dict[str, Any]]:
        for line in text.splitlines():
            line = line.strip()
            if line:
                yield json.loads(line)

    @staticmethod
    def parse_csv(text: str) -> Iterator[dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            yield {k: v for k, v in row.items() if k and v not in (None, "")}

    @staticmethod
    def parse_bundle(payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
        events = payload.get("events") or payload.get("data") or []
        if isinstance(events, list):
            yield from events

    def load_file(self, path: Path, source: str | None = None) -> tuple[int, int]:
        """Ingest a local .jsonl / .json / .csv replay file (path already validated)."""
        source = source or f"file:{path.name}"
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() == ".csv":
            it: Iterator[dict[str, Any]] = self.parse_csv(text)
        elif path.suffix.lower() == ".json":
            data = json.loads(text)
            it = iter(data if isinstance(data, list) else [data])
        else:
            it = self.parse_jsonl(text)
        accepted = rejected = 0
        for item in it:
            a, r = self.ingest_raw([item], source)
            accepted += a
            rejected += r
        log.info("ingested file %s: accepted=%d rejected=%d", path.name, accepted, rejected)
        return accepted, rejected
