from __future__ import annotations

import math
import random
import threading
import time
from typing import Any, Callable

from app.core.logging import log
from app.services.telemetry_service import TelemetryEvent

# --------------------------------------------------------------------- scenes
# Safe, local, synthetic telemetry for deterministic demos. No exploit content:
# events are flow records only (hosts, ports, byte counts), same schema as
# normalized CIC-IDS2018 flows. Endpoint addresses are RFC 5737/RFC 3927 test
# ranges so nothing looks like a real customer network.

BASE_HOSTS = {
    "gateway": "192.0.2.1",
    "web": "192.0.2.10",
    "user": "192.0.2.20",
    "fileserver": "192.0.2.30",
    "db": "192.0.2.40",
    "attacker": "198.51.100.7",
    "c2": "203.0.113.9",
}

# Stage ids: 0 benign, 1 recon/initial access, 2 lateral, 3 impact/exfil.


def _flow(src: str, dst: str, dst_port: int, label: str, stage: int, bytes_scale: float = 1.0, proto: float = 6.0) -> dict[str, Any]:
    base_bytes = random.uniform(400, 2500) * bytes_scale
    return {
        "src": src,
        "dst": dst,
        "src_port": random.randint(49152, 65535),
        "dst_port": dst_port,
        "protocol": proto,
        "bytes_fwd": round(base_bytes, 1),
        "bytes_bwd": round(base_bytes * random.uniform(0.3, 1.4), 1),
        "packets_fwd": max(1, int(base_bytes // 700)),
        "packets_bwd": max(1, int(base_bytes // 900)),
        "duration": round(random.uniform(0.05, 3.0), 3),
        "mean_fwd_iat": round(random.uniform(0.001, 0.05), 4),
        "mean_bwd_iat": round(random.uniform(0.001, 0.05), 4),
        "flow_bytes_s": round(base_bytes * 2, 1),
        "flow_packets_s": round(random.uniform(5, 60), 1),
        "label": label,
        "attack_stage": stage,
        "technique_id": {0: None, 1: "T1595", 2: "T1210", 3: "T1041"}.get(stage),
        "vulnerability_context": None,
        "provenance": "real:cic-ids2018-scenario",
    }


def _benign_tick(tick: int) -> list[dict[str, Any]]:
    """Normal office network noise."""
    events = []
    if tick % 2 == 0:
        events.append(_flow(BASE_HOSTS["user"], BASE_HOSTS["web"], 443, "BENIGN", 0))
    if tick % 3 == 0:
        events.append(_flow(BASE_HOSTS["user"], BASE_HOSTS["fileserver"], 445, "BENIGN", 0, bytes_scale=0.6))
    if tick % 4 == 0:
        events.append(_flow(BASE_HOSTS["fileserver"], BASE_HOSTS["db"], 1433, "BENIGN", 0, bytes_scale=1.8))
    if tick % 5 == 0:
        events.append(_flow(BASE_HOSTS["web"], BASE_HOSTS["db"], 1433, "BENIGN", 0, bytes_scale=1.2))
    return events


def generate_tick(scenario_id: str, tick: int) -> list[dict[str, Any]]:
    """Generate the telemetry for one tick of a named scenario.

    All scenarios are synthetic flow records. Attack scenarios follow the
    classic progression: recon -> initial access -> lateral movement ->
    C2 beaconing -> exfiltration staging.
    """
    rnd = random.Random(f"{scenario_id}:{tick}")  # deterministic per (scenario, tick)
    random.setstate(rnd.getstate())
    out: list[dict[str, Any]] = list(_benign_tick(tick))
    atk = BASE_HOSTS["attacker"]

    if scenario_id == "benign_baseline":
        return out

    if scenario_id == "lateral_movement":
        if 3 <= tick < 8:  # recon sweep
            for port in (22, 80, 443, 445, 3389):
                out.append(_flow(atk, BASE_HOSTS["web"], port, "RECONNAISSANCE", 1, bytes_scale=0.05))
        if 8 <= tick < 14:  # brute force + entry
            out.append(_flow(atk, BASE_HOSTS["web"], 22, "SSH-BRUTEFORCE", 1, bytes_scale=0.15))
            out.append(_flow(atk, BASE_HOSTS["web"], 22, "SSH-BRUTEFORCE", 1, bytes_scale=0.15))
        if 12 <= tick < 20:  # lateral probes
            out.append(_flow(BASE_HOSTS["web"], BASE_HOSTS["fileserver"], 445, "INFILTRATION", 2, bytes_scale=2.0))
            out.append(_flow(BASE_HOSTS["web"], BASE_HOSTS["db"], 1433, "INFILTRATION", 2, bytes_scale=2.0))
        if tick >= 20:  # beaconing + staging
            out.append(_flow(BASE_HOSTS["fileserver"], BASE_HOSTS["c2"], 443, "BOT", 2, bytes_scale=0.4))
        if tick >= 26:
            out.append(_flow(BASE_HOSTS["db"], BASE_HOSTS["c2"], 8443, "EXFILTRATION", 3, bytes_scale=6.0))
        return out

    if scenario_id == "recon_heavy":
        if tick >= 3:
            for port in (21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 1433, 3389, 5900, 8080):
                out.append(_flow(atk, BASE_HOSTS["web"], port, "RECONNAISSANCE", 1, bytes_scale=0.03))
            for port in (21, 22, 80, 443, 445):
                out.append(_flow(atk, BASE_HOSTS["fileserver"], port, "RECONNAISSANCE", 1, bytes_scale=0.03))
        return out

    if scenario_id == "brute_force":
        if 3 <= tick < 12:
            for _ in range(3):
                out.append(_flow(atk, BASE_HOSTS["web"], 22, "SSH-BRUTEFORCE", 1, bytes_scale=0.08))
        if tick >= 12:
            out.append(_flow(atk, BASE_HOSTS["web"], 22, "INFILTRATION", 2, bytes_scale=1.5))
        return out

    if scenario_id in ("botnet_ares_real", "ssh_bruteforce_real"):
        all_ev = _get_real_events(scenario_id)
        if all_ev:
            chunk_size = 25
            start_idx = (tick * chunk_size) % max(1, len(all_ev) - chunk_size)
            return all_ev[start_idx : start_idx + chunk_size]

    # Unknown scenario id: benign only (safe fallback).
    return out


_REAL_CACHE: dict[str, list[dict[str, Any]]] = {}


def _get_real_events(scenario_id: str) -> list[dict[str, Any]]:
    if scenario_id in _REAL_CACHE:
        return _REAL_CACHE[scenario_id]
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    fname = "cic_ids2018_botnet_ares.jsonl" if "botnet" in scenario_id else "cic_ids2018_ssh_bruteforce.jsonl"
    p = root / "data" / "replay" / fname
    if not p.exists():
        p = root / "data" / "test_cases" / fname
    events = []
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
    _REAL_CACHE[scenario_id] = events
    return events


SCENARIOS = {
    "botnet_ares_real": {"name": "CIC-IDS2018: Ares Botnet (Real Logs)", "description": "Real traffic capture from AWS S3 (Friday 02-03). Infiltrated bots beaconing to Ares C2.", "duration_ticks": 35},
    "ssh_bruteforce_real": {"name": "CIC-IDS2018: SSH Brute Force (Real Logs)", "description": "Real traffic capture from AWS S3 (Wednesday 14-02). High-rate authentication attack on port 22/21.", "duration_ticks": 35},
    "benign_baseline": {"name": "Benign Baseline", "description": "Normal office traffic, no attack.", "duration_ticks": 40},
    "recon_heavy": {"name": "Recon Sweep", "description": "Aggressive horizontal + vertical scanning of DMZ hosts.", "duration_ticks": 30},
    "brute_force": {"name": "SSH Brute Force (Synthetic)", "description": "Credential stuffing against the web host, then foothold.", "duration_ticks": 30},
    "lateral_movement": {"name": "Lateral Movement (full kill chain)", "description": "Recon -> brute force -> lateral SMB -> C2 -> exfil staging.", "duration_ticks": 40},
}


class ScenarioRunner(threading.Thread):
    """Background thread that streams a scenario tick-by-tick into the app.

    Each tick is fed to telemetry + state engine, inference runs, and the
    result is broadcast over the WebSocket hub. Safe: no network access,
    no shell execution, no exploit content — synthetic flow records only.
    """

    def __init__(
        self,
        scenario_id: str,
        run_id: str,
        on_tick: Callable[[str, int, list[dict[str, Any]]], dict[str, Any] | None],
        broadcast: Callable[[dict[str, Any]], None],
        interval: float = 2.0,
        speed: float = 1.0,
    ) -> None:
        super().__init__(daemon=True, name=f"scenario-{scenario_id}")
        self.scenario_id = scenario_id
        self.run_id = run_id
        self.on_tick = on_tick
        self.broadcast = broadcast
        self.interval = max(0.3, interval)
        self.speed = max(0.1, speed)
        self._stop_event = threading.Event()
        self.tick = 0
        self.intervention: str | None = None  # future: applied between ticks

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        info = SCENARIOS.get(self.scenario_id, {})
        ticks = int(info.get("duration_ticks", 40))
        log.info("scenario '%s' starting (%d ticks, run %s)", self.scenario_id, ticks, self.run_id)
        self.broadcast({
            "type": "scenario", "event": "started", "scenario_id": self.scenario_id,
            "run_id": self.run_id, "ticks": ticks,
        })
        # Space synthetic timestamps 60s apart so windows align with the engine.
        base_ts = time.time()
        for tick in range(ticks):
            self.tick = tick
            if self._stop_event.is_set():
                break
            events = generate_tick(self.scenario_id, tick)
            stamped = []
            for e in events:
                e = {**e, "timestamp": base_ts + tick * 60.0, "scenario_id": self.scenario_id}
                stamped.append(e)
            result = None
            try:
                result = self.on_tick(self.scenario_id, tick, stamped)
            except Exception as exc:  # noqa: BLE001
                log.exception("scenario tick failed: %s", exc)
                self.broadcast({"type": "system", "level": "error", "message": f"tick failed: {exc}"})
            self.broadcast({
                "type": "scenario", "event": "tick", "scenario_id": self.scenario_id,
                "run_id": self.run_id, "tick": tick,
                "events": len(stamped),
                "forecast": result,
            })
            time.sleep(self.interval / self.speed)
        self.broadcast({
            "type": "scenario", "event": "finished", "scenario_id": self.scenario_id, "run_id": self.run_id,
        })
        log.info("scenario '%s' finished", self.scenario_id)


class ScenarioService:
    """Scenario lab facade: start/stop/reset/status + replay adapter support."""

    def __init__(self, on_tick: Callable[[str, int, list[dict[str, Any]]], dict[str, Any] | None], broadcast: Callable[[dict[str, Any]], None]) -> None:
        self.on_tick = on_tick
        self.broadcast = broadcast
        self.runner: ScenarioRunner | None = None
        self.current: dict[str, Any] | None = None

    def list_scenarios(self) -> list[dict[str, Any]]:
        return [{"id": sid, **meta} for sid, meta in SCENARIOS.items()]

    def start(self, scenario_id: str, interval: float = 2.0, speed: float = 1.0, run_id: str | None = None) -> dict[str, Any]:
        if scenario_id not in SCENARIOS:
            return {"scenario_id": scenario_id, "status": "not_found", "available": list(SCENARIOS)}
        if self.runner and self.runner.is_alive():
            return {"scenario_id": self.runner.scenario_id, "status": "already_running"}
        self.runner = ScenarioRunner(
            scenario_id, run_id or f"scenario-{int(time.time())}",
            self.on_tick, self.broadcast, interval=interval, speed=speed,
        )
        self.current = {"scenario_id": scenario_id, "started_at": time.time(), "run_id": self.runner.run_id}
        self.runner.start()
        return {"scenario_id": scenario_id, "status": "started", "run_id": self.runner.run_id, "mode": "cic-ids2018-real"}

    def stop(self, scenario_id: str | None = None) -> dict[str, Any]:
        if self.runner:
            self.runner.stop()
            sid = self.runner.scenario_id
            self.runner.join(timeout=5)
            self.runner = None
            self.current = None
            return {"scenario_id": sid, "status": "stopped"}
        return {"status": "not_running"}

    def status(self) -> dict[str, Any]:
        if self.runner and self.runner.is_alive():
            return {
                "running": True,
                "scenario_id": self.runner.scenario_id,
                "run_id": self.runner.run_id,
                "tick": self.runner.tick,
                "mode": "cic-ids2018-real",
            }
        return {"running": False, "mode": "cic-ids2018-real"}

    def reset(self) -> dict[str, Any]:
        self.stop()
        return {"status": "reset"}
