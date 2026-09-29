from __future__ import annotations

"""All CYBERMIND API routes (REST + WebSocket), implemented against the
endpoint surface defined in docs/APP_BUILD_SPEC.md."""

import json
import hashlib
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

import asyncio

from app.adapters.strix import AuthorizationError, StrixRunner
from app.core.logging import log
from app.services.counterfactual_service import CounterfactualService, risk_band
from app.services.defence_service import DefenceService
from app.services.experiment_store import ExperimentStore
from app.services.forecast_service import ForecastService
from app.services.model_runtime import ModelRuntime, ModelUnavailableError
from app.services.replay_service import ReplayService
from app.services.scenario_runner import ScenarioService
from app.services.state_engine import STAGE_IDS, STAGE_NAMES, StateEngine, StateEngineConfig, parse_epoch
from app.services.patch_service import PatchService
from app.services.attack_lab_service import AttackLabService
from app.services.telemetry_service import TelemetryEvent, TelemetryService
from app.services.validation_service import ValidationService
from app.services.strix_timeline_evidence import compare_sandbox_stage_evidence
from app.services.local_sandbox_validation import run_local_sandbox_validation
from app.services.websocket_service import hub
from app.services.analyst_chat import answer_question
from cybermind.data.pcap_extract import PACKET_FEATURES
from cybermind.data.stages import STAGE_NAMES as MODEL_STAGE_NAMES

router = APIRouter(prefix="/api")
ws_router = APIRouter()  # mounted at app root: spec requires /ws/live

# --------------------------------------------------------------------- wiring
# Singletons created by app.main and injected here via init_router().
runtime: ModelRuntime
telemetry: TelemetryService
state_engine: StateEngine
forecast_service: ForecastService
counterfactual: CounterfactualService
experiments: ExperimentStore
scenarios: ScenarioService
replay: ReplayService
replay_dir: Path
strix_runner: StrixRunner
validation: ValidationService
defence: DefenceService
test_cases_dir: Path
attack_lab: AttackLabService | None = None
patch_service: PatchService | None = None
defence: DefenceService
test_cases_dir: Path
on_event_callback: Any = None

# Recent forecasts keyed by forecast_id (bounded, newest last).
forecast_history: list[dict[str, Any]] = []
FORECAST_HISTORY_MAX = 100


def _local_validation_dir() -> Path:
    path = experiments.root / "local_validation"
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.get("/validation/local")
def list_local_validations():
    runs = []
    for path in sorted(_local_validation_dir().glob("local-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
        try:
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return {"runs": runs}


@router.post("/validation/local")
async def local_validation():
    """Exercise the fixed bundled target without Strix or external targets."""
    if not state_engine.ready():
        raise HTTPException(status_code=409, detail="Load a capture or sample and generate a forecast first")
    # A loaded case can have a usable state before the user opens Forecast.
    # Freeze a fresh prediction for this check instead of leaving it disabled.
    forecast = run_forecast()
    if not forecast or not forecast.get("available", True):
        raise HTTPException(status_code=409, detail="Generate a forecast before running the local sandbox check")
    result = await run_local_sandbox_validation(forecast)
    path = _local_validation_dir() / f"{result['run_id']}.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2), encoding="utf-8")
    temporary.replace(path)
    return result


def init_router(
    rt: ModelRuntime,
    tel: TelemetryService,
    eng: StateEngine,
    fc: ForecastService,
    cf: CounterfactualService,
    ex: ExperimentStore,
    sc: ScenarioService,
    rp: ReplayService,
    rdir: Path,
    sx: StrixRunner | None = None,
    vd: ValidationService | None = None,
    df: DefenceService | None = None,
    tdir: Path | None = None,
    al: AttackLabService | None = None,
    ps: PatchService | None = None,
) -> None:
    global runtime, telemetry, state_engine, forecast_service, counterfactual, experiments, scenarios, replay, replay_dir
    global strix_runner, validation, defence, test_cases_dir, attack_lab, patch_service
    runtime, telemetry, state_engine, forecast_service = rt, tel, eng, fc
    counterfactual, experiments, scenarios, replay, replay_dir = cf, ex, sc, rp, rdir
    strix_runner = sx
    validation = vd
    defence = df if df is not None else DefenceService()
    test_cases_dir = tdir if tdir is not None else (rdir.parent / "test_cases")
    attack_lab = al
    patch_service = ps if ps is not None else PatchService()


# --------------------------------------------------------------------- schemas
class TelemetryBatch(BaseModel):
    events: list[TelemetryEvent] = Field(min_length=1, max_length=5000)


class ChatQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class ScenarioRequest(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=64)
    interval: float = 2.0
    speed: float = 1.0


class CounterfactualRequest(BaseModel):
    action: Literal["auto", "all", "No Action", "Block Host", "Block Port", "Isolate Host", "Restrict Edge", "Rate Limit"] = "auto"
    host: str | None = None
    port: int | None = None
    edge: list[int] | None = None
    k: int = Field(default=6, ge=1, le=24)


class GravityRequest(BaseModel):
    k: int = Field(default=6, ge=1, le=24)


class ReplayLoadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=128)


class ReplaySeekRequest(BaseModel):
    index: int = Field(ge=0)


class TestCaseLoadRequest(BaseModel):
    testcase_id: str = Field(min_length=1, max_length=128)
    limit: int = Field(default=1500, ge=50, le=50000)
    clear_previous: bool = True


class ReplaySession:
    """In-memory replay buffer for the UI timestamp scrubber."""

    def __init__(self) -> None:
        self.buffer: list[dict[str, Any]] = []
        self.filename: str | None = None
        self.index: int = 0

    def load(self, path: Path) -> int:
        events = [e for e in replay.stream(path) if isinstance(e, dict)]
        events.sort(key=lambda e: str(e.get("timestamp", "")))
        self.buffer = events
        self.filename = path.name
        self.index = 0
        return len(events)


replay_session = ReplaySession()


# ------------------------------------------------------------- shared pipeline
def _ingest_and_react(events: list[dict[str, Any]], source: str, run_id: str | None = None) -> dict[str, Any]:
    """Shared ingestion -> state rebuild -> inference -> broadcast pipeline."""
    accepted, rejected = telemetry.ingest_raw(events, source)
    for e in telemetry.latest(accepted):
        state_engine.append(e)
    if on_event_callback:
        try:
            on_event_callback(events)
        except Exception as exc:  # noqa: BLE001
            log.warning("event callback failed: %s", exc)
    forecast = None
    if state_engine.ready():
        forecast = run_forecast(run_id=run_id)
    hub.broadcast_sync({
        "type": "state",
        "source": source,
        "accepted": accepted,
        "rejected": rejected,
        "event_count": len(telemetry),
        "forecast": forecast,
    })
    return {"accepted": accepted, "rejected": rejected, "event_count": len(telemetry), "forecast": forecast}


def run_forecast(run_id: str | None = None, k: int | None = None) -> dict[str, Any]:
    states = state_engine.recent_sequence(8)
    try:
        result = forecast_service.from_states(states, k=k, run_id=run_id)
    except ModelUnavailableError:
        return forecast_service.unavailable("model_checkpoint_missing")
    if run_id:
        experiments.append_prediction(run_id, {
            "timestamp": time.time(),
            "risk": result["horizon"]["risk"],
            "stage_id": result["horizon"]["stage_id"],
            "confidence": result["confidence"],
        })
    # Register in forecast history so validations can reference a forecast_id.
    if result.get("available", True):
        result = {**result, "forecast_id": uuid.uuid4().hex[:12], "forecast_ts": time.time()}
        forecast_history.append({k2: v for k2, v in result.items()})
        if len(forecast_history) > FORECAST_HISTORY_MAX:
            forecast_history.pop(0)
    hub.broadcast_sync({"type": "forecast", "run_id": run_id, **result})
    return result


# ---------------------------------------------------------------------- health
@router.get("/health")
def health():
    model_health = runtime.health()
    return {
        "status": "ok",
        "model": model_health,
        "telemetry_events": len(telemetry),
        "state_windows": len(state_engine.build_states()),
        "scenario": scenarios.status(),
        "time": time.time(),
    }


@router.get("/model")
def model_info():
    return runtime.meta if runtime.meta.get("available") else runtime.load()


@router.post("/chat")
def chat(question: ChatQuestion):
    """Answer read-only questions from the current local app session."""
    recent_validation = list_local_validations()["runs"]
    model_status = {**runtime.health(), **runtime.meta}
    return answer_question(
        question.question,
        events=telemetry.latest(len(telemetry)),
        state=state_engine.snapshot(),
        forecast=forecast_history[-1] if forecast_history else None,
        model=model_status,
        validation=recent_validation[0] if recent_validation else None,
        strix_available=bool(strix_runner and strix_runner.availability().get("available")),
    )


# ------------------------------------------------------------------- telemetry
@router.post("/telemetry/events")
def ingest_events(batch: TelemetryBatch):
    events = [e.model_dump() for e in batch.events]
    return _ingest_and_react(events, source="api")


@router.post("/telemetry/replay")
def replay_telemetry(request: ScenarioRequest):
    """Replay a local JSONL/CSV file from data/replay as telemetry."""
    path = (replay_dir / f"{request.scenario_id}.jsonl").resolve()
    if replay_dir.resolve() not in path.parents:
        raise HTTPException(status_code=400, detail="invalid scenario path")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"no replay file {path.name}")
    events = list(replay.stream(path))
    result = _ingest_and_react(events, source=f"replay:{path.name}")
    return {"file": path.name, **result}


@router.post("/telemetry/upload")
async def upload_telemetry(file: UploadFile = File(...)):
    """Upload a local .jsonl / .json / .csv telemetry file for replay."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".jsonl", ".json", ".csv"}:
        raise HTTPException(status_code=400, detail="supported: .jsonl, .json, .csv")
    target = (replay_dir / Path(file.filename or "upload.jsonl").name).resolve()
    if replay_dir.resolve() not in target.parents:
        raise HTTPException(status_code=400, detail="invalid filename")
    target.write_bytes(await file.read())
    accepted, rejected = telemetry.load_file(target, source=f"upload:{target.name}")
    for e in telemetry.latest(accepted):
        state_engine.append(e)
    forecast = run_forecast() if state_engine.ready() else None
    return {"file": target.name, "accepted": accepted, "rejected": rejected, "forecast": forecast}


# ----------------------------------------------------------------------- state
@router.get("/state/current")
def current_state():
    snap = state_engine.snapshot()
    if snap is None:
        return {"nodes": [], "edges": [], "event_count": len(telemetry), "labels": {}, "ready": False}
    return {
        "timestamp": snap.timestamp,
        "window_start": snap.window_start,
        "window_end": snap.window_end,
        "event_count": snap.event_count,
        "nodes": snap.nodes,
        "edges": snap.edges,
        "labels": snap.labels,
        "dominant_stage": snap.dominant_stage,
        "label_counts": snap.label_counts,
        "ready": state_engine.ready(),
    }


@router.get("/timeline")
def timeline(limit: int = 100):
    return {"events": telemetry.latest(max(1, min(limit, 1000)))}


# -------------------------------------------------------------------- forecast
@router.get("/forecast")
def forecast(k: int | None = None):
    if not state_engine.ready():
        return forecast_service.unavailable("insufficient_observation_windows")
    return run_forecast(k=k)


@router.post("/explain/{host_index}")
def explain(host_index: int, k: int = 4):
    state = state_engine.current_state()
    if state is None:
        raise HTTPException(status_code=404, detail="no graph state available")
    if host_index < 0 or host_index >= state.x.shape[0]:
        raise HTTPException(status_code=400, detail="host index out of range")
    try:
        attributions = runtime.explain(state, k=k, topk=10)
    except ModelUnavailableError:
        raise HTTPException(status_code=503, detail="model unavailable: checkpoint missing")
    total = sum(a["attribution"] for a in attributions) or 1.0
    for a in attributions:
        a["share"] = round(a["attribution"] / total, 4)
    node_id = state.node_ids[host_index] if host_index < len(state.node_ids) else str(host_index)
    return {
        "host": node_id,
        "host_index": host_index,
        "attributions": attributions,
        "disclaimer": "Gradient × input attribution from the trained model. Evidence, not causal proof.",
    }


# -------------------------------------------------------------- counterfactual
@router.post("/counterfactual/simulate")
def counterfactual_simulate(req: CounterfactualRequest):
    state = state_engine.current_state()
    if state is None:
        raise HTTPException(status_code=404, detail="no graph state available")
    try:
        result = counterfactual.simulate(state, action=req.action, host=req.host, port=req.port, edge=req.edge, k=req.k)
    except ModelUnavailableError:
        raise HTTPException(status_code=503, detail="model unavailable: checkpoint missing")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if req.action == "auto" and result.get("recommended"):
        hub.broadcast_sync({"type": "intervention", "recommended": result["recommended"], "baseline": result["baseline"]})
    return result


@router.post("/counterfactual/attack-gravity")
def attack_gravity(req: GravityRequest):
    state = state_engine.current_state()
    if state is None:
        raise HTTPException(status_code=404, detail="no graph state available")
    try:
        return counterfactual.attack_gravity(state, k=req.k)
    except ModelUnavailableError:
        raise HTTPException(status_code=503, detail="model unavailable: checkpoint missing")


# -------------------------------------------------------------------- scenarios
@router.get("/scenarios")
def list_scenarios():
    return {"scenarios": scenarios.list_scenarios(), "status": scenarios.status()}


@router.post("/scenarios/start")
def scenario_start(req: ScenarioRequest):
    run = experiments.create_run(scenario_id=req.scenario_id, model_version=runtime.version, source="scenario")
    result = scenarios.start(req.scenario_id, interval=req.interval, speed=req.speed, run_id=run["run_id"])
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"unknown scenario: {req.scenario_id}")
    if result.get("status") == "already_running":
        raise HTTPException(status_code=409, detail="another scenario is already running")
    return {**result, "run_id": run["run_id"]}


@router.post("/scenarios/stop")
def scenario_stop(req: ScenarioRequest):
    return scenarios.stop(req.scenario_id)


@router.post("/scenarios/reset")
def scenario_reset():
    scenarios.reset()
    telemetry.events.clear()
    state_engine.clear()
    return {"status": "reset"}


@router.get("/scenarios/status")
def scenario_status():
    return scenarios.status()


# ---------------------------------------------------------------------- replay
@router.get("/replay/files")
def replay_files():
    files = sorted(
        p.name for p in replay_dir.iterdir() if p.suffix.lower() in {".jsonl", ".json", ".csv"}
    ) if replay_dir.exists() else []
    return {"files": files, "loaded": replay_session.filename, "buffer": len(replay_session.buffer), "index": replay_session.index}


@router.post("/replay/load")
def replay_load(req: ReplayLoadRequest):
    path = (replay_dir / req.filename).resolve()
    if replay_dir.resolve() not in path.parents or path.suffix.lower() not in {".jsonl", ".json", ".csv"}:
        raise HTTPException(status_code=400, detail="invalid replay filename")
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    try:
        count = replay_session.load(path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"parse failed: {exc}")
    return {"file": path.name, "events": count, "index": 0}


@router.post("/replay/seek")
def replay_seek(req: ReplaySeekRequest):
    if not replay_session.buffer:
        raise HTTPException(status_code=404, detail="no replay loaded")
    idx = min(req.index, len(replay_session.buffer))
    prefix = replay_session.buffer[:idx]
    # Scrubbing rebuilds state from scratch so windows match the prefix exactly.
    telemetry.events.clear()
    state_engine.clear()
    accepted, _ = telemetry.ingest_raw(prefix, source=f"replay:{replay_session.filename}")
    for e in telemetry.latest(accepted):
        state_engine.append(e)
    replay_session.index = idx
    forecast = run_forecast() if state_engine.ready() else None
    snap = state_engine.snapshot()
    return {
        "index": idx,
        "total": len(replay_session.buffer),
        "event_count": accepted,
        "ready": state_engine.ready(),
        "forecast": forecast,
        "state": {
            "nodes": snap.nodes if snap else [],
            "edges": snap.edges if snap else [],
            "dominant_stage": snap.dominant_stage if snap else 0,
        },
    }


# ------------------------------------------------------------------ test cases
AVAILABLE_TESTCASES = [
    {
        "id": "botnet_ares",
        "name": "CIC-IDS2018: Ares Botnet (Real Logs)",
        "description": "Real traffic capture from AWS S3 CSE-CIC-IDS2018 (Friday 02-03-2018). Compromised Ares bot nodes executing C2 beaconing to external controller.",
        "filename": "cicids2018_friday_02_03_botnet_sample.csv",
        "replay_file": "cic_ids2018_botnet_ares.jsonl",
        "attack_type": "Botnet / C2 Beaconing",
        "stage": "EXECUTION / LATERAL",
        "attack_stage": 2,
        "events_count": 15079,
        "size_mb": 4.5,
        "provenance": "REAL DATASET",
        "target": "18.219.211.138",
    },
    {
        "id": "ssh_bruteforce",
        "name": "CIC-IDS2018: SSH/FTP Brute Force (Real Logs)",
        "description": "Real traffic capture from AWS S3 CSE-CIC-IDS2018 (Wednesday 14-02-2018). High-volume credential stuffing against SSH (port 22) and FTP (port 21).",
        "filename": "cicids2018_wednesday_14_02_bruteforce_sample.csv",
        "replay_file": "cic_ids2018_ssh_bruteforce.jsonl",
        "attack_type": "Credential Access / Brute Force",
        "stage": "RECON / INITIAL ACCESS",
        "attack_stage": 1,
        "events_count": 21310,
        "size_mb": 4.5,
        "provenance": "REAL DATASET",
        "target": "172.31.69.25 (Port 22/21)",
    },
]


def _load_testcase_events(testcase_id: str, limit: int = 1500) -> list[dict[str, Any]]:
    import json
    import csv

    tid = testcase_id.lower().replace("-", "_").strip()
    events: list[dict[str, Any]] = []

    jsonl_map = {
        "botnet_ares": "cic_ids2018_botnet_ares.jsonl",
        "botnet": "cic_ids2018_botnet_ares.jsonl",
        "friday": "cic_ids2018_botnet_ares.jsonl",
        "ssh_bruteforce": "cic_ids2018_ssh_bruteforce.jsonl",
        "bruteforce": "cic_ids2018_ssh_bruteforce.jsonl",
        "wednesday": "cic_ids2018_ssh_bruteforce.jsonl",
    }
    csv_map = {
        "botnet_ares": "cicids2018_friday_02_03_botnet_sample.csv",
        "botnet": "cicids2018_friday_02_03_botnet_sample.csv",
        "friday": "cicids2018_friday_02_03_botnet_sample.csv",
        "ssh_bruteforce": "cicids2018_wednesday_14_02_bruteforce_sample.csv",
        "bruteforce": "cicids2018_wednesday_14_02_bruteforce_sample.csv",
        "wednesday": "cicids2018_wednesday_14_02_bruteforce_sample.csv",
    }

    target_jsonl = jsonl_map.get(tid)
    if target_jsonl:
        p = (replay_dir / target_jsonl).resolve()
        if not p.exists() and test_cases_dir:
            p = (test_cases_dir / target_jsonl).resolve()
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
                        if len(events) >= limit:
                            break
            if events:
                return events

    target_csv = csv_map.get(tid)
    csv_path = None
    if target_csv and test_cases_dir:
        candidate = (test_cases_dir / target_csv).resolve()
        if candidate.exists():
            csv_path = candidate
        else:
            bundled = Path(__file__).resolve().parents[2] / "examples" / "test_cases" / target_csv
            if bundled.is_file():
                csv_path = bundled
    elif test_cases_dir:
        candidate = (test_cases_dir / testcase_id).resolve()
        if candidate.exists():
            csv_path = candidate

    if csv_path and csv_path.exists():
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            is_raw_cicids = "Label" in (reader.fieldnames or [])
            for idx, r in enumerate(reader):
                if idx >= limit:
                    break
                if is_raw_cicids:
                    # Raw CSE-CIC-IDS2018 export: map native columns to the
                    # unified event schema with topological reconstruction.
                    label = (r.get("Label") or "Benign").strip()
                    try:
                        dst_port = float(r.get("Dst Port") or 80)
                    except (TypeError, ValueError):
                        dst_port = 80.0
                    proto = float(r.get("Protocol") or 6)

                    if "bot" in label.lower():
                        src = "172.31.69.14"
                        dst = "18.219.211.138" if dst_port != 53 else "172.31.0.2"
                        stage = 2
                        tech = "T1071"
                    elif "bruteforce" in label.lower():
                        src = "18.218.115.60"
                        dst = "172.31.69.25"
                        stage = 1
                        tech = "T1110"
                    else:
                        src = "172.31.69.28" if idx % 2 == 0 else "172.31.69.29"
                        dst = "172.31.69.25" if dst_port in (21, 22, 80) else "172.31.0.2"
                        stage = 0
                        tech = None

                    ts_str = r.get("Timestamp", "")
                    timestamp = parse_epoch(ts_str)
                    if timestamp is None:
                        from datetime import datetime as _dt
                        try:
                            timestamp = _dt.strptime(ts_str, "%d/%m/%Y %H:%M:%S").timestamp()
                        except Exception:  # noqa: BLE001
                            timestamp = 1518597000.0 + idx * 2.0

                    def _f(col: str) -> float:
                        try:
                            v = r.get(col, "0")
                            if v in ("Infinity", "NaN", "", None):
                                return 0.0
                            return float(v)
                        except (TypeError, ValueError):
                            return 0.0

                    events.append({
                        "timestamp": timestamp,
                        "src": src,
                        "dst": dst,
                        "src_port": 50000 + (idx % 1000),
                        "dst_port": dst_port,
                        "protocol": proto,
                        "duration": _f("Flow Duration") / 1e6,
                        "bytes_fwd": _f("TotLen Fwd Pkts"),
                        "bytes_bwd": _f("TotLen Bwd Pkts"),
                        "packets_fwd": _f("Tot Fwd Pkts"),
                        "packets_bwd": _f("Tot Bwd Pkts"),
                        "flow_bytes_s": _f("Flow Byts/s"),
                        "flow_packets_s": _f("Flow Pkts/s"),
                        "mean_fwd_iat": _f("Fwd IAT Mean"),
                        "mean_bwd_iat": _f("Bwd IAT Mean"),
                        "label": label,
                        "attack_stage": stage,
                        "technique_id": tech,
                        "provenance": f"REAL DATASET:{csv_path.name}",
                    })
                else:
                    # Bundled normalized sample (timestamp,src,dst,... schema).
                    timestamp = parse_epoch(r.get("timestamp"))
                    if timestamp is None:
                        continue
                    event = {key: value for key, value in r.items() if value not in (None, "")}
                    event["timestamp"] = timestamp
                    event["provenance"] = f"real_flow_sample:{csv_path.name}"
                    events.append(event)
        return events

    return []


@router.get("/testcases")
def list_testcases():
    """List downloaded real CIC-IDS2018 test cases available for one-click load."""
    return {"testcases": AVAILABLE_TESTCASES}


@router.post("/testcases/load")
def load_testcase(req: TestCaseLoadRequest):
    """Load a real CIC-IDS2018 test case into the live analysis pipeline."""
    events = _load_testcase_events(req.testcase_id, limit=req.limit)
    if not events:
        raise HTTPException(status_code=404, detail=f"No events found for test case: {req.testcase_id}")

    if req.clear_previous:
        telemetry.events.clear()
        state_engine.clear()

    accepted, rejected = telemetry.ingest_raw(events, source=f"real:testcase:{req.testcase_id}")
    for e in telemetry.latest(accepted):
        state_engine.append(e)

    forecast = run_forecast() if state_engine.ready() else None
    snap = state_engine.snapshot()

    hub.broadcast_sync({
        "type": "state",
        "source": f"real:testcase:{req.testcase_id}",
        "accepted": accepted,
        "rejected": rejected,
        "event_count": len(telemetry),
        "forecast": forecast,
    })

    meta = next((t for t in AVAILABLE_TESTCASES if t["id"] == req.testcase_id), None)
    testcase_name = meta["name"] if meta else req.testcase_id

    return {
        "status": "loaded",
        "testcase_id": req.testcase_id,
        "name": testcase_name,
        "accepted": accepted,
        "rejected": rejected,
        "event_count": len(telemetry),
        "state_windows": len(state_engine.build_states()),
        "ready": state_engine.ready(),
        "forecast": forecast,
        "state": {
            "nodes": snap.nodes if snap else [],
            "edges": snap.edges if snap else [],
            "dominant_stage": snap.dominant_stage if snap else 0,
            "labels": snap.labels if snap else {},
        },
    }


# ------------------------------------------------------------------ PS Element B.2: Flagged-Flows Table
@router.get("/flows/flagged")
def get_flagged_flows(limit: int = 60, min_risk: float = 0.0):
    """Show per-flow rule hints; the model forecasts aggregate graph windows."""
    flows = []
    events = list(telemetry.events)
    if not events:
        sample_events = _load_testcase_events("testcase-bruteforce", limit=30)
        events = sample_events if sample_events else []

    recent_events = events[-250:]
    # A known SSH brute-force label is a source annotation, not a model score.
    # Use the observed rate of attempts to distinguish an isolated attempt from
    # a sustained burst. This also keeps raw, unlabeled PCAP flows unassessed.
    auth_burst_counts: dict[int, int] = {}
    attempts: dict[tuple[str, str, int], deque[float]] = defaultdict(deque)
    for index, event in sorted(enumerate(recent_events), key=lambda item: float(item[1].get("timestamp") or 0)):
        label_text = str(event.get("label") or "").lower()
        if "bruteforce" not in label_text and "ssh" not in label_text:
            continue
        timestamp = float(event.get("timestamp") or 0)
        key = (str(event.get("src") or ""), str(event.get("dst") or ""), int(event.get("dst_port") or 0))
        window = attempts[key]
        while window and window[0] < timestamp - 10.0:
            window.popleft()
        window.append(timestamp)
        auth_burst_counts[index] = len(window)

    for i, e in reversed(list(enumerate(recent_events))):
        stage = int(e.get("attack_stage") or 0)
        label = str(e.get("label") or "BENIGN")
        unassessed = label in {"PCAP_EVENT", "PCAP_INSPECTED", "UPLOADED_FLOW"}
        bytes_fwd = float(e.get("bytes_fwd") or 0)
        bytes_bwd = float(e.get("bytes_bwd") or 0)
        tot_bytes = bytes_fwd + bytes_bwd

        base_risk = 0.02
        if unassessed:
            # Raw packet captures contain no reference attack stage. Stage 6 is
            # Unknown/Ambiguous, never evidence of a critical attack flow.
            base_risk = 0.0
        elif stage == 1 and ("bruteforce" in label.lower() or "ssh" in label.lower()):
            # Medium for early attempts; critical only after six observed
            # attempts from the same source to the same target in ten seconds.
            base_risk = 0.92 if auth_burst_counts.get(i, 0) >= 6 else 0.40
        elif stage == 1:
            base_risk = 0.65
        elif stage == 2:
            base_risk = 0.85
        elif stage == 3:
            base_risk = 0.92
        elif 4 <= stage <= 5:
            base_risk = 0.98
        elif "bruteforce" in label.lower() or "sql" in label.lower():
            base_risk = 0.78
        elif "bot" in label.lower() or "c2" in label.lower():
            base_risk = 0.94

        if tot_bytes > 4000 and not unassessed and not (stage == 1 and ("bruteforce" in label.lower() or "ssh" in label.lower())):
            base_risk = min(0.99, base_risk + 0.05)

        if base_risk < min_risk:
            continue

        band = "UNASSESSED" if unassessed else risk_band(base_risk)
        proto_num = int(e.get("protocol") or 6)
        proto_str = "TCP" if proto_num == 6 else "UDP" if proto_num == 17 else f"IP/{proto_num}"
        stage_name = (
            "Unknown (unlabeled)" if unassessed
            else MODEL_STAGE_NAMES[stage] if 0 <= stage < len(MODEL_STAGE_NAMES) else "Unknown"
        )

        flows.append({
            "flow_id": f"flow-{i+1:04d}",
            "timestamp": e.get("timestamp"),
            "src": e.get("src", "0.0.0.0"),
            "dst": e.get("dst", "0.0.0.0"),
            "src_port": int(e.get("src_port") or 0),
            "dst_port": int(e.get("dst_port") or 0),
            "protocol": proto_str,
            "duration": round(float(e.get("duration") or 0.0), 3),
            "bytes_fwd": bytes_fwd,
            "bytes_bwd": bytes_bwd,
            "tot_bytes": tot_bytes,
            "packets_fwd": int(e.get("packets_fwd") or 0),
            "packets_bwd": int(e.get("packets_bwd") or 0),
            "label": label,
            "stage_id": stage,
            "predicted_stage": stage_name,
            "technique_id": e.get("technique_id") or "",
            "risk_score": round(base_risk, 3),
            "risk_pct": round(base_risk * 100, 1),
            "risk_band": band,
        })
        if len(flows) >= limit:
            break

    flows.sort(key=lambda x: x["risk_score"], reverse=True)
    return {
        "count": len(flows),
        "score_source": "rule_based_flow_hint_not_model_prediction",
        "flows": flows,
        "summary": {
            "critical_count": sum(1 for f in flows if f["risk_band"] == "CRITICAL"),
            "high_count": sum(1 for f in flows if f["risk_band"] == "HIGH"),
            "medium_count": sum(1 for f in flows if f["risk_band"] == "MEDIUM"),
            "low_or_benign_count": sum(1 for f in flows if f["risk_band"] in ("LOW", "BENIGN")),
            "unassessed_count": sum(1 for f in flows if f["risk_band"] == "UNASSESSED"),
        },
    }


# ------------------------------------------------------------------ PS Element B.1: PCAP & CSV Upload
@router.post("/upload/flows")
async def upload_network_flows(file: UploadFile = File(...), clear_previous: bool = False):
    """PS Element B.1: Upload PCAP or CSV flow export with fuzzy column matching and instant inference."""
    filename = file.filename or "uploaded_flows"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    events: list[dict[str, Any]] = []
    is_pcap = filename.lower().endswith((".pcap", ".pcapng", ".cap"))
    if not is_pcap and not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Supported uploads: .pcap, .pcapng, .cap, .csv")

    if is_pcap:
        import tempfile
        from cybermind.data.pcap_extract import pcap_to_dataframe
        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            df = pcap_to_dataframe(tmp_path)
            for _, row in df.iterrows():
                events.append({
                    "timestamp": row["timestamp"].timestamp() if hasattr(row["timestamp"], "timestamp") else time.time(),
                    "src": str(row.get("src", "127.0.0.1")),
                    "dst": str(row.get("dst", "127.0.0.1")),
                    "src_port": int(row.get("src_port") or 0),
                    "dst_port": int(row.get("dst_port") or 80),
                    "protocol": int(row.get("protocol") or 6),
                    "duration": float(row.get("duration") or 0.0),
                    "bytes_fwd": float(row.get("bytes_fwd") or 0.0),
                    "bytes_bwd": float(row.get("bytes_bwd") or 0.0),
                    "packets_fwd": float(row.get("packets_fwd") or 0.0),
                    "packets_bwd": float(row.get("packets_bwd") or 0.0),
                    "flow_bytes_s": float(row.get("flow_bytes_s") or 0.0),
                    "flow_packets_s": float(row.get("flow_packets_s") or 0.0),
                    "mean_fwd_iat": float(row.get("mean_fwd_iat") or 0.0),
                    "mean_bwd_iat": float(row.get("mean_bwd_iat") or 0.0),
                    "label": str(row.get("label", "PCAP_INSPECTED")),
                    "attack_stage": int(row.get("stage") or 0),
                    "technique_id": None,
                    "provenance": f"pcap_upload:{filename}",
                    **{name: float(row.get(name) or 0.0) for name in PACKET_FEATURES},
                })
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"PCAP parsing error: {exc}")
        finally:
            import os
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    else:
        import csv
        import io
        text = content.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            raise HTTPException(status_code=400, detail="CSV contains no records.")

        cols = list(rows[0].keys())
        def find_col(candidates):
            normalize = lambda name: name.strip().lower().replace(" ", "").replace("_", "").replace(".", "")
            for cand in candidates:
                for col in cols:
                    if normalize(col) == normalize(cand):
                        return col
            for cand in candidates:
                for col in cols:
                    if normalize(cand) in normalize(col):
                        return col
            return None

        c_src = find_col(["srcip", "sourceip", "src", "ipsrc", "source"])
        c_dst = find_col(["dstip", "destip", "destinationip", "dst", "ipdst", "destination"])
        c_sport = find_col(["srcport", "sourceport", "sport", "tcpsrcport"])
        c_dport = find_col(["dstport", "destport", "destinationport", "dport", "tcpdstport", "port"])
        c_proto = find_col(["protocol", "proto"])
        c_dur = find_col(["flowduration", "duration"])
        c_time = find_col(["timestamp", "flowstart", "starttime", "datefirstseen"])
        c_bytes = find_col(["totlenfwdpkts", "fwdbytes", "bytesfwd", "totalfwdbytes", "bytes", "totbytes", "length"])
        c_bytes_bwd = find_col(["totlenbwdpkts", "bwdbytes", "bytesbwd", "totalbwdbytes"])
        c_pkts_fwd = find_col(["totfwdpkts", "packetsfwd", "fwdpackets"])
        c_pkts_bwd = find_col(["totbwdpkts", "packetsbwd", "bwdpackets"])
        c_label = find_col(["label", "class", "attack", "category", "tag"])
        if not c_src or not c_dst:
            raise HTTPException(status_code=400, detail="CSV needs source and destination IP columns.")

        for idx, r in enumerate(rows[:2000]):
            src = str(r.get(c_src, "192.168.1.10"))
            dst = str(r.get(c_dst, "192.168.1.1"))
            sport = int(float(r.get(c_sport) or 50000 + (idx % 1000))) if c_sport else 50000 + (idx % 1000)
            dport = int(float(r.get(c_dport) or 80)) if c_dport else 80
            proto = 6 if "tcp" in str(r.get(c_proto, "")).lower() or not c_proto else 17 if "udp" in str(r.get(c_proto, "")).lower() else int(float(r.get(c_proto) or 6))
            duration = float(r.get(c_dur) or 0.05) if c_dur else 0.05
            if duration > 1000:
                duration /= 1e6
            bytes_val = float(r.get(c_bytes) or 256.0) if c_bytes else 256.0
            bytes_bwd = float(r.get(c_bytes_bwd) or 0.0) if c_bytes_bwd else 0.0
            label_val = str(r.get(c_label, "UPLOADED_FLOW")) if c_label else "UPLOADED_FLOW"

            stage = 0
            tech = None
            lbl_lower = label_val.lower()
            if any(k in lbl_lower for k in ("bruteforce", "ssh", "auth", "login")):
                stage = 1
                tech = "T1110"
            elif any(k in lbl_lower for k in ("sql", "injection", "exploit", "cve")):
                stage = 1
                tech = "T1190"
            elif any(k in lbl_lower for k in ("smb", "lateral", "admin", "rpc")):
                stage = 2
                tech = "T1021"
            elif any(k in lbl_lower for k in ("bot", "c2", "beacon", "command")):
                stage = 3
                tech = "T1071"
            elif any(k in lbl_lower for k in ("exfil", "steal", "leak")):
                stage = 5
                tech = "T1048"

            raw_time = r.get(c_time) if c_time else None
            if raw_time not in (None, ""):
                try:
                    timestamp = parse_epoch(float(raw_time))
                except (ValueError, TypeError):
                    timestamp = parse_epoch(raw_time)
                if timestamp is None:
                    raise HTTPException(status_code=400, detail=f"Invalid timestamp in CSV row {idx + 2}.")
            else:
                # Timestamp-free flow exports have no observed chronology.
                # Keep a disclosed one-minute demo spacing, never a subsecond burst.
                timestamp = time.time() - (len(rows) - idx) * 60.0

            events.append({
                "timestamp": timestamp,
                "src": src,
                "dst": dst,
                "src_port": sport,
                "dst_port": dport,
                "protocol": proto,
                "duration": duration,
                "bytes_fwd": bytes_val,
                "bytes_bwd": bytes_bwd,
                "packets_fwd": float(r.get(c_pkts_fwd) or 0.0) if c_pkts_fwd else 0.0,
                "packets_bwd": float(r.get(c_pkts_bwd) or 0.0) if c_pkts_bwd else 0.0,
                "flow_bytes_s": bytes_val / max(duration, 0.001),
                "flow_packets_s": float(r.get(c_pkts_fwd) or 0.0) / max(duration, 0.001) if c_pkts_fwd else 0.0,
                "mean_fwd_iat": duration / 4,
                "mean_bwd_iat": duration / 4,
                "label": label_val,
                "attack_stage": stage,
                "technique_id": tech,
                "provenance": f"csv_upload:{filename}",
                **{name: float(r.get(name) or 0.0) for name in PACKET_FEATURES},
            })

    if not events:
        raise HTTPException(status_code=400, detail="No valid flow events could be parsed from the file.")

    if clear_previous:
        telemetry.events.clear()
        state_engine.clear()

    accepted, rejected = telemetry.ingest_raw(events, source=f"upload:{filename}")
    for e in telemetry.latest(accepted):
        state_engine.append(e)

    forecast = run_forecast() if state_engine.ready() else None

    hub.broadcast_sync({
        "type": "state",
        "source": f"upload:{filename}",
        "accepted": accepted,
        "rejected": rejected,
        "event_count": len(telemetry),
        "forecast": forecast,
    })

    return {
        "status": "success",
        "filename": filename,
        "flows_ingested": accepted,
        "total_events": len(telemetry),
        "forecast": forecast,
        "state_ready": state_engine.ready(),
        "time_basis": "source_timestamps" if is_pcap or c_time else "assumed_60s_spacing",
    }


# ------------------------------------------------------------------ PS Track A: Benchmark Comparison
@router.get("/benchmark/comparison")
def get_benchmark_comparison():
    """Return the saved, audited comparison only for the checkpoint it evaluated."""
    # `routes.py` is /app/app/api/routes.py in Docker, where parents[4] does not
    # exist. Resolve evidence relative to the application root so the same code
    # works in the repository, Docker image, and frozen desktop build.
    application_root = Path(__file__).resolve().parents[2]
    evidence_candidates = (
        application_root / "results" / "final_grouped_model_comparison.json",
        application_root / "results" / "final_grouped" / "model_comparison.json",
    )
    evidence_file = next((candidate for candidate in evidence_candidates if candidate.is_file()), None)
    expected_sha = "5324902ca017e946af58b41fbd576561553d7c03b532b37ee9255f4a3677cf39"
    if evidence_file is None or not runtime.checkpoint_path.is_file():
        raise HTTPException(status_code=503, detail="Verified comparison or checkpoint is unavailable.")
    with runtime.checkpoint_path.open("rb") as checkpoint:
        digest = hashlib.file_digest(checkpoint, "sha256").hexdigest()
    if digest != expected_sha:
        raise HTTPException(status_code=409, detail="Saved comparison does not match the loaded checkpoint.")
    try:
        evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
        test = evidence["test"]
        model = test["world_model"]
        baseline = test["feature_matched_logistic"]
        difference = test["absolute_metric_difference"]
        future_window_decisions = evidence["summary"]["future_window_decisions"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="Verified comparison evidence is unreadable.") from exc
    return {
        "title": "CYBERMIND vs feature-matched logistic regression",
        "problem_statement": "SIH26153",
        "dataset": "Capture-grouped CIC-IDS2018 held-out test split",
        "dataset_flows_evaluated": future_window_decisions,
        "calibration_constraint": "Fixed threshold 0.5; four observed windows predict four unseen windows",
        "source": "Saved sample-level test predictions; no new inference in this UI",
        "checkpoint_sha256": digest,
        "models": {
            "cybermind_world_model": {
                "name": "CYBERMIND best.pt (GATv2 + temporal model; argmax stage decoder)",
                "parameters": runtime.meta.get("parameters"),
                "metrics": model["metrics"],
                "confusion_matrix": model["confusion_counts"],
            },
            "logistic_baseline": {
                "name": "Feature-matched logistic regression",
                "metrics": baseline["metrics"],
                "confusion_matrix": baseline["confusion_counts"],
            },
        },
        "deltas_vs_logistic": {
            "f1_delta": f"{difference['f1'] * 100:+.2f} pp",
            "precision_delta": f"{difference['precision'] * 100:+.2f} pp",
            "recall_delta": f"{difference['recall'] * 100:+.2f} pp",
            "fpr_reduction": f"{difference['fpr'] * 100:+.2f} pp",
            "ap_delta": f"{difference['ap'] * 100:+.2f} pp",
        },
        "verdict": (
            "On this capture-grouped test split, saved predictions favor the loaded checkpoint "
            "for binary infiltration forecasting. Stage macro-F1 is 0.2443; this does not "
            "establish correct full kill-chain forecasting or performance on a new network."
        ),
    }



# ------------------------------------------------------------------ experiments
@router.get("/experiments")
def list_experiments(limit: int = 50):
    return {"runs": experiments.list_runs(limit)}


@router.get("/experiments/{run_id}")
def get_experiment(run_id: str):
    record = experiments.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run not found")
    return record


# ------------------------------------------------------- forecast (v2 surface)
class ForecastGenerateRequest(BaseModel):
    k: int = Field(default=12, ge=1, le=24)


@router.get("/forecast/current")
def forecast_current():
    """Latest forecast with its stable forecast_id (for validation referencing)."""
    if forecast_history:
        return forecast_history[-1]
    return run_forecast()


@router.post("/forecast/generate")
def forecast_generate(req: ForecastGenerateRequest):
    if not state_engine.ready():
        return forecast_service.unavailable("insufficient_observation_windows")
    return run_forecast(k=req.k)


@router.get("/forecast/{forecast_id}")
def forecast_by_id(forecast_id: str):
    for f in reversed(forecast_history):
        if f.get("forecast_id") == forecast_id:
            return f
    raise HTTPException(status_code=404, detail="forecast not found")


# ------------------------------------------------------------- strix validation
class TargetRegisterRequest(BaseModel):
    target: str = Field(min_length=1, max_length=512)
    environment: Literal["SANDBOX", "REPLAY", "AUTHORIZED_TEST"]
    label: str = Field(default="", max_length=128)
    notes: str = Field(default="", max_length=512)


class StrixRunRequest(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=64)
    target: str | None = Field(default=None, max_length=512)
    instruction: str | None = Field(default=None, max_length=2000)
    scan_mode: Literal["quick", "standard", "deep"] = "quick"
    max_budget: float | None = Field(default=None, gt=0)
    autonomous: bool = False


class ValidationStartRequest(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=64)
    target: str | None = Field(default=None, max_length=512)
    scan_mode: Literal["quick", "standard", "deep"] = "quick"
    max_budget: float | None = Field(default=None, gt=0)


class SandboxStageEventRequest(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    source: Literal["sandbox_event_log"]
    stage_id: Literal[3, 5]
    timestamp: float = Field(allow_inf_nan=False)
    evidence_ref: str = Field(min_length=1, max_length=512)
    verified_by: str = Field(min_length=1, max_length=128)
    strix_finding_ids: list[str] = Field(default_factory=list, max_length=100)


class StageEvidenceCompareRequest(BaseModel):
    events: list[SandboxStageEventRequest] = Field(default_factory=list, max_length=100)


class DefenceDecisionRequest(BaseModel):
    recommendation_id: str = Field(min_length=1, max_length=64)
    approver: str = Field(default="analyst", max_length=64)
    reason: str = Field(default="", max_length=300)


@router.get("/strix/status")
def strix_status():
    import os
    import shutil
    import subprocess
    import urllib.request

    availability = strix_runner.availability() if strix_runner else {"available": False, "reason": "not wired"}
    targets = strix_runner.gate.list_targets() if strix_runner else []
    sandbox_online = False
    try:
        with urllib.request.urlopen("http://127.0.0.1:8081/sandbox/health", timeout=0.4) as response:
            sandbox_online = response.status == 200
    except (OSError, TimeoutError):
        pass
    docker_ready = False
    docker_cli_present = bool(shutil.which("docker"))
    if docker_cli_present:
        try:
            docker_ready = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=2, check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            pass
    llm_configured = bool(os.getenv("VALIDATOR_LLM") or os.getenv("STRIX_LLM")) and bool(
        os.getenv("LLM_API_KEY") or os.getenv("LLM_API_BASE")
    )
    reasons = []
    if not availability.get("available"):
        reasons.append("Strix CLI not found (set VALIDATOR_BIN)")
    if not docker_ready:
        reasons.append(
            "Docker CLI not installed in app runtime" if not docker_cli_present
            else "Docker engine not accessible from app runtime"
        )
    if not sandbox_online:
        reasons.append("local sandbox target at 127.0.0.1:8081 is offline")
    if not llm_configured:
        reasons.append("Strix LLM provider not configured")
    return {
        **availability,
        "ready": not reasons,
        "reason": "; ".join(reasons) if reasons else None,
        "checks": {
            "cli": bool(availability.get("available")),
            "docker": docker_ready,
            "sandbox": sandbox_online,
            "llm": llm_configured,
        },
        "targets": targets,
    }


@router.get("/strix/targets")
def strix_targets():
    return {"targets": strix_runner.gate.list_targets()}


@router.post("/strix/targets")
def strix_register_target(req: TargetRegisterRequest):
    try:
        reg = strix_runner.gate.register(req.target, req.environment, req.label, req.notes)
    except AuthorizationError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": str(exc)})
    return reg.to_dict()


@router.delete("/strix/targets")
def strix_unregister_target(target: str):
    ok = strix_runner.gate.unregister(target)
    if not ok:
        raise HTTPException(status_code=404, detail="target not registered")
    return {"unregistered": target}


@router.get("/strix/runs")
def strix_runs(limit: int = 50):
    return {"runs": strix_runner.list_runs(limit), "availability": strix_runner.availability()}


@router.get("/strix/runs/{run_id}")
def strix_run_detail(run_id: str):
    rec = strix_runner.get_run(run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="strix run not found")
    return rec


@router.post("/strix/runs")
async def strix_start_run(req: StrixRunRequest):
    """Launch an authorized Strix run. Target must be registered (safety gate)."""
    from app.adapters.strix.schemas import StrixRunConfig

    use_target = req.target or (validation.default_target_for(req.scenario_id) or {}).get("target")
    if not use_target:
        raise HTTPException(status_code=400, detail={"code": "NO_TARGET", "message": "no target provided or registered for scenario"})
    try:
        rec = await strix_runner.start_run(StrixRunConfig(
            scenario_id=req.scenario_id,
            target=use_target,
            instruction=req.instruction or "Authorized CYBERMIND validation scan.",
            scan_mode=req.scan_mode,
            max_budget=req.max_budget or settings_strix_budget(),
        ), autonomous=req.autonomous)
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code, "message": str(exc)})
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "VALIDATION_UNAVAILABLE", "message": str(exc)})
    hub.broadcast_sync({"type": "strix.run_started", **rec})
    return rec


def settings_strix_budget() -> float | None:
    from app.core.config import settings
    return settings.strix_max_budget


@router.post("/strix/runs/{run_id}/stop")
async def strix_stop_run(run_id: str):
    rec = await strix_runner.stop_run(run_id)
    if rec.get("error"):
        raise HTTPException(status_code=404, detail=rec["error"])
    hub.broadcast_sync({"type": "strix.run_completed", **rec})
    return rec


@router.get("/strix/runs/{run_id}/findings")
def strix_run_findings(run_id: str):
    rec = strix_runner.get_run(run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="strix run not found")
    parsed = strix_runner.get_parsed(run_id)
    if parsed is None:
        return {"run": rec, "parsed": None, "note": "no artifacts collected yet"}
    return {"run": rec, "parsed": parsed}


@router.post("/scenarios/{scenario_id}/validate")
async def scenario_validate(scenario_id: str, req: ValidationStartRequest | None = None):
    """Full validation loop: forecast snapshot -> authorized Strix run ->
    evidence parsing -> prediction-vs-observed comparison -> experiment."""
    req = req or ValidationStartRequest(scenario_id=scenario_id)
    scenario_id = req.scenario_id or scenario_id
    if not state_engine.ready():
        raise HTTPException(status_code=409, detail={"code": "INSUFFICIENT_CONTEXT", "message": "feed telemetry before validating"})
    snap = state_engine.snapshot()
    forecast = forecast_history[-1] if forecast_history else None
    if not forecast or not forecast.get("available", True):
        raise HTTPException(status_code=409, detail={"code": "NO_FORECAST", "message": "generate a forecast first"})

    prediction = {
        "stage_id": forecast.get("horizon", {}).get("stage_id"),
        "risk": forecast.get("horizon", {}).get("risk"),
        "entities": [n.get("id") for n in (snap.nodes if snap else [])][:12],
    }
    result = await validation.validate(
        scenario_id=scenario_id,
        prediction=prediction,
        target=req.target,
        scan_mode=req.scan_mode,
        max_budget=req.max_budget,
        forecast_id=forecast.get("forecast_id"),
        forecast_ts=forecast.get("forecast_ts"),
    )
    if result.get("error") == "VALIDATION_UNAUTHORIZED":
        raise HTTPException(status_code=403, detail=result)
    if result.get("error") == "VALIDATION_UNAVAILABLE":
        raise HTTPException(status_code=503, detail=result)
    comparison = result["comparison"]
    # Persist as an experiment record (first-class, queryable).
    exp = experiments.create_run(scenario_id=scenario_id, model_version=runtime.version, source="validation")
    experiments.append_prediction(exp["run_id"], {
        "type": "validation",
        "forecast_id": comparison.get("forecast_id"),
        "strix_run_id": comparison.get("strix_run_id"),
        "predicted": {"stage": comparison.get("predicted_stage_label"), "risk": comparison.get("predicted_risk")},
        "observed": {
            "stage": comparison.get("observed_stage_label"),
            "stage_inferred": comparison.get("observed_stage_inferred"),
            "risk_estimate": comparison.get("observed_risk_estimate"),
            "finding_count": comparison.get("finding_count"),
            "max_severity": comparison.get("max_severity"),
        },
        "match": comparison.get("match"),
        "prediction_error": comparison.get("prediction_error"),
        "lead_time": comparison.get("lead_time"),
    })
    experiments.close_run(exp["run_id"], metrics={"match": comparison.get("match")})
    hub.broadcast_sync({"type": "validation.completed", **comparison})
    return {"experiment_id": exp["run_id"], **result}


@router.get("/scenarios/{scenario_id}/validation")
def scenario_validation_list(scenario_id: str):
    return {"validations": [c for c in validation.list_comparisons() if c.get("scenario_id") == scenario_id]}


@router.get("/validations")
def validation_list(limit: int = 50):
    return {"validations": validation.list_comparisons(limit)}


@router.get("/validations/{validation_id}")
def validation_detail(validation_id: str):
    c = validation.get_comparison(validation_id)
    if c is None:
        raise HTTPException(status_code=404, detail="validation not found")
    return c


@router.post("/validations/{validation_id}/stage-evidence")
def compare_validation_stage_evidence(validation_id: str, req: StageEvidenceCompareRequest):
    """Compare one frozen forecast with reviewer-attested events from its sandbox run."""
    comparison = validation.get_comparison(validation_id)
    if comparison is None:
        raise HTTPException(status_code=404, detail="validation not found")
    forecast = next((f for f in reversed(forecast_history)
                     if f.get("forecast_id") == comparison.get("forecast_id")), None)
    if forecast is None:
        raise HTTPException(status_code=409, detail="frozen forecast is no longer available")
    run = strix_runner.get_run(comparison["strix_run_id"])
    if run is None:
        raise HTTPException(status_code=409, detail="linked Strix run is no longer available")
    registration = strix_runner.gate.get(run.get("target", ""))
    if registration is None or registration.environment.value != "SANDBOX":
        raise HTTPException(status_code=403, detail="stage evidence requires a registered sandbox run")
    if run.get("status") not in ("completed", "completed_findings"):
        raise HTTPException(status_code=409, detail="linked Strix run is not complete")
    parsed = strix_runner.get_parsed(run["run_id"]) or {}
    try:
        report = compare_sandbox_stage_evidence(
            forecast, run, parsed, [event.model_dump() for event in req.events],
            step_seconds=state_engine.config.stride_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record = experiments.create_run(
        scenario_id=comparison.get("scenario_id"), model_version=runtime.version,
        source="sandbox_stage_evidence",
    )
    experiments.append_prediction(record["run_id"], report)
    experiments.close_run(record["run_id"], metrics={
        str(stage["stage_id"]): stage["verdict"] for stage in report["stages"]
    })
    return {"experiment_id": record["run_id"], **report}


# ----------------------------------------------------------------- defence API
@router.get("/defence/recommendation")
def defence_recommendation():
    """Current best recommendation from the latest counterfactual + validations."""
    state = state_engine.current_state()
    if state is None:
        raise HTTPException(status_code=409, detail={"code": "INSUFFICIENT_CONTEXT", "message": "no graph state"})
    cf = counterfactual.simulate(state, action="auto", k=6)
    # Map recent validations to intervention keys (action:host) so the ranking
    # layer can use real validation evidence.
    vals: dict[str, dict[str, Any]] = {}
    for c in validation.list_comparisons(10):
        if c.get("match") not in ("MATCH", "PARTIAL", "MISMATCH"):
            continue
        entities = c.get("observed_entities") or []
        predicted = [e for e in c.get("predicted_entities") or [] if e]
        host = entities[0] if entities else (predicted[0] if predicted else "")
        vals.setdefault(f"Isolate Host:{host}", c)
    rec = defence.recommend(cf["baseline"], cf["interventions"], vals)
    hub.broadcast_sync({"type": "defence.recommendation", **rec})
    return rec


@router.post("/defence/simulate")
def defence_simulate(req: CounterfactualRequest):
    """Counterfactual simulation returning a ranked defence package."""
    state = state_engine.current_state()
    if state is None:
        raise HTTPException(status_code=404, detail="no graph state available")
    try:
        cf = counterfactual.simulate(state, action=req.action, host=req.host, port=req.port, edge=req.edge, k=req.k)
    except ModelUnavailableError:
        raise HTTPException(status_code=503, detail="model unavailable: checkpoint missing")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    rec = defence.recommend(cf["baseline"], cf["interventions"])
    return {"counterfactual": cf, "recommendation": rec}


@router.post("/defence/approve")
async def defence_approve(req: DefenceDecisionRequest):
    decision = defence.approve(req.recommendation_id, req.approver)
    if decision.get("error"):
        raise HTTPException(status_code=404, detail=decision["error"])
    hub.broadcast_sync({"type": "approval.granted", **decision})
    return decision


@router.post("/defence/reject")
async def defence_reject(req: DefenceDecisionRequest):
    decision = defence.reject(req.recommendation_id, req.approver, req.reason)
    if decision.get("error"):
        raise HTTPException(status_code=404, detail=decision["error"])
    hub.broadcast_sync({"type": "approval.rejected", **decision})
    return decision


@router.get("/defence/pending")
def defence_pending():
    return {"pending": defence.pending()}


# ------------------------------------------------------------- attack lab & strix
class AttackLabProbeRequest(BaseModel):
    vector_id: str = Field(default="ssh_bruteforce", max_length=64)
    scan_mode: Literal["quick", "standard", "deep"] = "quick"
    intensity: int = Field(default=15, ge=3, le=50)
    target_ip: str | None = Field(default=None, max_length=64)
    target_port: int | None = Field(default=None)


class SuggestHostPatchRequest(BaseModel):
    host: str = Field(min_length=1, max_length=64)
    vector_id: str | None = Field(default=None, max_length=64)
    port: int | None = Field(default=None)


class PatchGenerateRequest(BaseModel):
    finding: dict[str, Any]


class OneClickPatchApplyRequest(BaseModel):
    patch_id: str = Field(min_length=1, max_length=64)
    approver: str = Field(default="analyst", max_length=64)


@router.get("/attack-lab/status")
def attack_lab_status():
    if not attack_lab:
        raise HTTPException(status_code=503, detail="Attack Lab service not initialized")
    return attack_lab.get_status()


@router.get("/attack-lab/vectors")
def attack_lab_vectors():
    if not attack_lab:
        raise HTTPException(status_code=503, detail="Attack Lab service not initialized")
    return {"vectors": attack_lab.list_available_vectors()}


@router.get("/attack-lab/risk-assessment")
def attack_lab_risk_assessment():
    """GNN-driven per-vector risk assessment (best_last.pt).

    Ranks all four vectors by the trained world model's assessed risk so the
    analyst can attack in model-priority order."""
    if not attack_lab:
        raise HTTPException(status_code=503, detail="Attack Lab service not initialized")
    return attack_lab.assess_vector_risks()


@router.post("/attack-lab/probe/start")
async def attack_lab_start_probe(req: AttackLabProbeRequest):
    if not attack_lab:
        raise HTTPException(status_code=503, detail="Attack Lab service not initialized")
    res = await attack_lab.start_probe(
        vector_id=req.vector_id,
        scan_mode=req.scan_mode,
        intensity=req.intensity,
        target_ip=req.target_ip,
        target_port=req.target_port,
    )
    if res.get("error"):
        raise HTTPException(status_code=409, detail=res["error"])
    return res


@router.post("/attack-lab/patch/suggest")
async def attack_lab_suggest_host_patch(req: SuggestHostPatchRequest):
    if not patch_service:
        raise HTTPException(status_code=503, detail="Patch service not initialized")
    vec_id = req.vector_id
    port = req.port or 22
    if not vec_id:
        if port == 8081 or port == 80:
            vec_id = "sqli_probe"
        elif port == 445:
            vec_id = "smb_lateral"
        elif port == 8080:
            vec_id = "c2_beacon"
        else:
            vec_id = "ssh_bruteforce"

    vec_info = {
        "finding_id": f"sug-{uuid.uuid4().hex[:6]}",
        "vector_id": vec_id,
        "title": f"Target Vulnerability on {req.host}:{port}",
        "target": f"{req.host}:{port}",
        "target_ip": req.host,
        "target_port": port,
        "severity": "HIGH",
    }
    patch = await patch_service.generate_patch(vec_info)
    return {"host": req.host, "vector_id": vec_id, "patch": patch}


@router.post("/attack-lab/probe/stop")
async def attack_lab_stop_probe():
    if not attack_lab:
        raise HTTPException(status_code=503, detail="Attack Lab service not initialized")
    return await attack_lab.stop_probe()


@router.get("/attack-lab/patches")
def attack_lab_list_patches():
    if not patch_service:
        raise HTTPException(status_code=503, detail="Patch service not initialized")
    return {"patches": patch_service.list_patches()}


@router.post("/attack-lab/patch/generate")
async def attack_lab_generate_patch(req: PatchGenerateRequest):
    if not patch_service:
        raise HTTPException(status_code=503, detail="Patch service not initialized")
    return await patch_service.generate_patch(req.finding)


@router.post("/attack-lab/patch/apply")
async def attack_lab_apply_patch(req: OneClickPatchApplyRequest):
    if not attack_lab:
        raise HTTPException(status_code=503, detail="Attack Lab service not initialized")
    res = await attack_lab.apply_one_click_patch(req.patch_id, approver=req.approver)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.get("/attack-lab/probe/records")
def attack_lab_probe_records():
    """Per-step probe records (real HTTP verdicts) of the latest session."""
    if not attack_lab:
        raise HTTPException(status_code=503, detail="Attack Lab service not initialized")
    session = attack_lab.current_session or {}
    return {
        "session_id": session.get("session_id"),
        "status": session.get("status"),
        "summary": session.get("summary"),
        "probe_records": session.get("probe_records", []),
        "verification": (session.get("generated_patch") or {}).get("verification"),
    }


@router.get("/attack-lab/ollama/status")
def attack_lab_ollama_status():
    if not patch_service:
        raise HTTPException(status_code=503, detail="Patch service not initialized")
    return patch_service.check_patch_engine_status()


@router.post("/attack-lab/sandbox/reset")
async def attack_lab_sandbox_reset():
    """Proxy reset to isolated target sandbox (http://127.0.0.1:8081).

    Also clears the backend's applied-patch registry so vector states stay
    consistent with the freshly reset sandbox (otherwise the UI would still
    show vectors as patched after a sandbox reset)."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            res = await client.post("http://127.0.0.1:8081/sandbox/reset")
            body = res.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reset sandbox: {e}")
    if patch_service is not None:
        patch_service._applied_patches.clear()
    if attack_lab is not None and attack_lab.current_session:
        attack_lab.current_session = None
    return body



# ------------------------------------------------------------------- websocket
@ws_router.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await hub.connect(ws)
    await ws.send_json({"type": "system", "status": "connected", "model": runtime.health()})
    try:
        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_json({"type": "system", "status": "alive"})
    except WebSocketDisconnect:
        hub.disconnect(ws)
    except Exception:  # noqa: BLE001
        hub.disconnect(ws)
