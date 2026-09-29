from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import init_router, router, ws_router
from app.adapters.strix import SafetyGate, StrixClient, StrixRunner
from app.core.config import Settings
from app.services.counterfactual_service import CounterfactualService
from app.services.defence_service import DefenceService
from app.services.experiment_store import ExperimentStore
from app.services.forecast_service import ForecastService
from app.services.model_runtime import ModelRuntime
from app.services.replay_service import ReplayService
from app.services.scenario_runner import ScenarioService
from app.services.state_engine import StateEngine, StateEngineConfig
from app.services.telemetry_service import TelemetryService
from app.services.validation_service import ValidationService
from app.services.patch_service import PatchService
from app.services.attack_lab_service import AttackLabService
from app.services.websocket_service import hub

web_dir = Path(__file__).resolve().parents[1] / "web"
# Prefer the built React SPA (frontend/dist); fall back to the legacy page.
dist_dir = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if (dist_dir / "index.html").exists():
    web_dir = dist_dir

app = FastAPI(title="CYBERMIND", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1", "http://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Service wiring (single load per process, per APP_BUILD_SPEC F1)
# ---------------------------------------------------------------------------
settings = Settings()
runtime = ModelRuntime(settings.model_path, settings.device)
telemetry = TelemetryService()
state_engine = StateEngine(StateEngineConfig())
forecast_service = ForecastService(runtime, rollout_steps=settings.rollout_steps)
counterfactual = CounterfactualService(runtime)
experiments = ExperimentStore(settings.runs_dir)
replay = ReplayService()

# Strix validation layer (authorized adversarial validation; optional at runtime).
_gate = SafetyGate()
_strix_client = StrixClient(
    strix_bin=settings.strix_bin,
    runs_dir=str(settings.strix_runs_dir),
    llm_model=settings.strix_llm,
    timeout=settings.strix_timeout,
    max_budget=settings.strix_max_budget,
)
strix_runner = StrixRunner(
    client=_strix_client,
    gate=_gate,
    artifacts_dir=settings.strix_runs_dir,
    default_timeout=settings.strix_timeout,
)
validation = ValidationService(strix_runner, _gate)
defence = DefenceService()
patch_service = PatchService()

def _run_forecast_hook(run_id: str | None = None) -> dict | None:
    from app.api.routes import run_forecast
    return run_forecast(run_id=run_id)

def _broadcast(message: dict) -> None:
    hub.broadcast_sync(message)

attack_lab = AttackLabService(
    gate=_gate,
    telemetry=telemetry,
    state_engine=state_engine,
    patch_service=patch_service,
    broadcast_fn=_broadcast,
    forecast_fn=_run_forecast_hook,
)

def _on_scenario_tick(scenario_id: str, tick: int, events: list[dict]) -> dict | None:
    """Feed one scenario tick through the standard pipeline; return forecast."""
    from app.api.routes import run_forecast  # local import avoids circular deps

    run_id = (scenarios.current or {}).get("run_id")
    for e in events:
        telemetry.ingest_raw([e], source=f"scenario:{scenario_id}")
        state_engine.append(e)
    if run_id:
        experiments.append_prediction(run_id, {"tick": tick, "events": len(events)})
    if state_engine.ready():
        return run_forecast(run_id=run_id)
    return None


scenarios = ScenarioService(on_tick=_on_scenario_tick, broadcast=_broadcast)

init_router(
    rt=runtime,
    tel=telemetry,
    eng=state_engine,
    fc=forecast_service,
    cf=counterfactual,
    ex=experiments,
    sc=scenarios,
    rp=replay,
    rdir=settings.replay_dir,
    sx=strix_runner,
    vd=validation,
    df=defence,
    tdir=settings.test_cases_dir,
    al=attack_lab,
    ps=patch_service,
)

app.include_router(router)
app.include_router(ws_router)


# ---------------------------------------------------------------------------
# Static offline UI (built SPA assets live under /assets)
# ---------------------------------------------------------------------------
app.mount("/assets", StaticFiles(directory=web_dir / "assets"), name="assets")

ui_copy_dir = Path(__file__).resolve().parents[1] / "ui_copy"
if ui_copy_dir.exists():
    app.mount("/ui-copy", StaticFiles(directory=ui_copy_dir, html=True), name="ui-copy")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(web_dir / "index.html")


@app.get("/incident-decrypter", include_in_schema=False)
def incident_decrypter():
    """Independent offline report viewer; no model or API dependency."""
    return FileResponse(Path(__file__).resolve().parents[1] / "tools" / "incident_decrypter" / "index.html")


@app.get("/{static_file:path}", include_in_schema=False)
def spa_fallback(static_file: str):
    """Serve SPA static files (favicon etc.); never shadows /api routes."""
    if ".." in static_file or static_file.startswith(("api", "ws")):
        raise FastAPIHTTPException(status_code=404, detail="not found")
    candidate = (web_dir / static_file).resolve()
    if web_dir.resolve() not in candidate.parents and candidate != (web_dir / "index.html").resolve():
        raise FastAPIHTTPException(status_code=404, detail="not found")
    if candidate.is_file():
        return FileResponse(candidate)
    raise FastAPIHTTPException(status_code=404, detail="not found")


@app.on_event("startup")
def startup_load_model() -> None:
    """Load the model once at startup; missing checkpoint is non-fatal."""
    meta = runtime.load()
    if not meta.get("available"):
        print(f"[CYBERMIND] model not loaded: {meta.get('reason')} — UI runs in degraded mode")
    # Register the built-in isolated SANDBOX validation targets (idempotent).
    validation.ensure_scenario_targets_registered()
    availability = strix_runner.availability()
    if not availability.get("available"):
        print(f"[CYBERMIND] Strix validation unavailable: {availability.get('reason')} — forecast continues")


@app.on_event("shutdown")
def shutdown_cleanup() -> None:
    strix_runner.shutdown()
