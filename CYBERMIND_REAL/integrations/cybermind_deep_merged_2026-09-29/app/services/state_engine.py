from __future__ import annotations

"""Temporal state engine.

Converts normalized telemetry events into time windows and graph states using
the existing ML data-layer primitives (graph_builder, temporal) so the app
never duplicates the research feature pipeline.

Windows are built incrementally (only the final partial window is re-aggregated
when new events arrive) and gap-aware: large empty time spans are skipped in
O(log n) instead of striding through them.
"""
import bisect
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from cybermind.data.graph_builder import NODE_FEATURE_NAMES, build_graph_state
from cybermind.data.pcap_extract import PACKET_FEATURES

CANON_COLS = [
    "timestamp", "src", "dst", "src_port", "dst_port", "protocol",
    "bytes_fwd", "bytes_bwd", "packets_fwd", "packets_bwd", "duration",
    "mean_fwd_iat", "mean_bwd_iat", "flow_bytes_s", "flow_packets_s",
    "label", "infiltration", "stage", *PACKET_FEATURES,
]
_NUM_COLS = CANON_COLS[3:15]
# ATT&CK-aligned coarse stage names (values are the research stage ids used
# throughout the ML core; see knowledge/stage_mapping.yaml).
STAGE_NAMES = {
    0: "BENIGN",
    1: "RECON / INITIAL ACCESS",
    2: "EXECUTION / LATERAL",
    3: "IMPACT / EXFIL",
}
STAGE_SHORT = {0: "Benign", 1: "Recon", 2: "Lateral", 3: "Impact"}
STAGE_IDS = ["T1595", "T1190", "T1210", "T1041"]
STAGE_TECHNIQUES = {
    0: "No adversarial technique observed",
    1: "Active Scanning / Exploit Public-Facing Application",
    2: "Remote Services: SMB / lateral tool transfer",
    3: "Exfiltration Over C2 Channel / Impact",
}


def parse_epoch(value: Any) -> float | None:
    """Robust epoch-seconds parsing for numbers and ISO-ish strings."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        unit = "ns" if v >= 1e18 else "us" if v >= 1e15 else "ms" if v >= 1e12 else "s"
        return pd.to_datetime(v, unit=unit).timestamp()
    try:
        ts = pd.to_datetime(value, errors="coerce")
        if ts is pd.NaT or pd.isna(ts):
            return None
        return float(ts.timestamp())
    except Exception:  # noqa: BLE001
        return None


@dataclass
class StateEngineConfig:
    window_seconds: float = 60.0
    stride_seconds: float = 30.0
    max_windows: int = 64
    min_sequence: int = 3


@dataclass
class StateSnapshot:
    """Serializable projection of the latest graph state for the UI."""
    timestamp: float
    window_start: float
    window_end: float
    event_count: int
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    labels: dict[str, int] = field(default_factory=dict)
    dominant_stage: int = 0
    label_counts: dict[str, int] = field(default_factory=dict)


class StateEngine:
    """Event buffer -> normalized flow frame -> rolling graph windows."""

    def __init__(self, config: StateEngineConfig | None = None) -> None:
        self.config = config or StateEngineConfig()
        self._events: list[dict[str, Any]] = []
        self._states: list[Any] = []  # GraphState objects
        self._snapshots: list[StateSnapshot] = []
        self._dirty = True
        self._min_epoch: float | None = None

    # ---------------------------------------------------------------- events
    def append(self, event: dict[str, Any]) -> None:
        self._events.append(event)
        epoch = parse_epoch(event.get("timestamp"))
        if epoch is not None and (self._min_epoch is None or epoch < self._min_epoch):
            # Older-than-expected event: full rebuild needed for correctness.
            self._min_epoch = epoch
            self._states = []
        self._dirty = True

    def extend(self, events: list[dict[str, Any]]) -> None:
        for e in events:
            self.append(e)

    def clear(self) -> None:
        self._events = []
        self._states = []
        self._snapshots = []
        self._dirty = True
        self._min_epoch = None

    def __len__(self) -> int:
        return len(self._events)

    # ------------------------------------------------------------- dataframe
    def to_frame(self, events: list[dict[str, Any]]) -> pd.DataFrame:
        rows = []
        for e in events:
            epoch = parse_epoch(e.get("timestamp"))
            if epoch is None:
                continue
            label = str(e.get("label") or "BENIGN")
            row = {
                "timestamp": pd.Timestamp(epoch, unit="s"),
                "src": str(e.get("src") or ""),
                "dst": str(e.get("dst") or ""),
                "label": label,
                "infiltration": 0.0 if label.upper() == "BENIGN" else 1.0,
                "stage": int(e.get("attack_stage") or 0),
            }
            for c in _NUM_COLS:
                row[c] = float(e.get(c) or 0.0)
            for c in PACKET_FEATURES:
                row[c] = float(e.get(c) or 0.0)
            rows.append(row)
        if not rows:
            return pd.DataFrame(columns=CANON_COLS)
        df = pd.DataFrame(rows)
        for c in _NUM_COLS:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        # datetime64[ns] keeps downstream ns-based epoch math portable.
        df["timestamp"] = df["timestamp"].astype("datetime64[ns]")
        return df.sort_values("timestamp").reset_index(drop=True)

    # ---------------------------------------------------------------- states
    def build_states(self, events: list[dict[str, Any]] | None = None) -> list[Any]:
        """Build windowed GraphState objects (incrementally when possible)."""
        if events is not None:
            return self._build_full(events)
        if not self._dirty and self._states:
            return self._states
        if not self._events:
            return []
        return self._build_incremental()

    def _build_full(self, events: list[dict[str, Any]]) -> list[Any]:
        return self._states_from_frame(self.to_frame(events))

    def _states_from_frame(self, df: pd.DataFrame) -> list[Any]:
        """Gap-aware windowing: O(events) instead of O(timespan/stride)."""
        if df.empty:
            return []
        times = (df.timestamp.astype("int64") / 1e9).tolist()
        win, stride = self.config.window_seconds, self.config.stride_seconds
        states: list[Any] = []
        n = len(times)
        t = times[0]
        while t <= times[-1] + 1e-6:
            j = bisect.bisect_left(times, t - 1e-9)
            k = bisect.bisect_left(times, t + win)
            if k > j:
                states.append(build_graph_state(df.iloc[j:k], "app_session", {"source": "app_state_engine"}))
                t += stride
            else:
                # Empty span: jump directly to the next event instead of striding.
                if j >= n:
                    break
                t = max(times[j], t + stride)
        return states[-self.config.max_windows:]

    def _build_incremental(self) -> list[Any]:
        """Re-aggregate only the last (partial) window plus any newer events."""
        resume: float | None = None
        if self._states:
            resume = float(self._states[-1].timestamp)
            self._states.pop()  # final window may not be complete yet
        if resume is None:
            self._states = []
        tail = [e for e in self._events if resume is None or (parse_epoch(e.get("timestamp")) or 0.0) >= resume]
        df = self.to_frame(tail)
        if df.empty:
            self._dirty = False
            return self._states
        new_states = self._states_from_frame(df)
        self._states.extend(new_states)
        self._states = self._states[-self.config.max_windows:]
        self._dirty = False
        return self._states

    def states(self) -> list[Any]:
        return self.build_states()

    def current_state(self) -> Any | None:
        states = self.build_states()
        return states[-1] if states else None

    def snapshot(self, state: Any | None = None) -> StateSnapshot | None:
        st = state or self.current_state()
        if st is None:
            return None
        nodes: list[dict[str, Any]] = []
        for i, nid in enumerate(st.node_ids):
            x = st.x[i].tolist() if hasattr(st.x, "tolist") else [0.0] * len(NODE_FEATURE_NAMES)
            nodes.append({
                "id": str(nid), "index": i,
                "anomaly": float(x[13]) if len(x) > 13 else 0.0,
                "activity": float(x[2]) if len(x) > 2 else 0.0,
            })
        edges: list[dict[str, Any]] = []
        ei = st.edge_index.t().tolist() if st.edge_index.numel() else []
        ea = st.edge_attr.tolist() if st.edge_attr.numel() else []
        for k, (a, b) in enumerate(ei):
            attr = ea[k] if k < len(ea) else []
            edges.append({
                "src": st.node_ids[a], "dst": st.node_ids[b], "src_index": int(a), "dst_index": int(b),
                "bytes": float(attr[0]) if attr else 0.0,
                "packets": float(attr[1]) if attr else 0.0,
                "protocol": float(attr[2]) if attr else 0.0,
                "port": float(attr[3]) if attr else 0.0,
                "duration": float(attr[5]) if attr else 0.0,
            })
        labels: dict[str, int] = {}
        for ev in self._events:
            labels[ev.get("label", "BENIGN")] = labels.get(ev.get("label", "BENIGN"), 0) + 1
        return StateSnapshot(
            timestamp=float(st.timestamp),
            window_start=float(st.timestamp),
            window_end=float(st.timestamp) + self.config.window_seconds,
            event_count=len(self._events),
            nodes=nodes,
            edges=edges,
            labels=labels,
            dominant_stage=int(st.y_stage),
            label_counts=labels,
        )

    # ------------------------------------------------------------- sequences
    def recent_sequence(self, k: int) -> list[Any]:
        """Last k graph states as a model-ready sequence."""
        states = self.build_states()
        return states[-k:] if len(states) >= k else states

    def ready(self) -> bool:
        return len(self.build_states()) >= self.config.min_sequence
