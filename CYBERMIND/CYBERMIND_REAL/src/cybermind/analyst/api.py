"""Authenticated localhost API for offline capture analysis."""
from __future__ import annotations
import json
import hashlib
import os
import secrets
import tempfile
from pathlib import Path
from threading import RLock

import torch
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from cybermind.analyst.case_qa import answer_case_question
from cybermind.analyst.case_security import account_path, create_account, decrypt_report, encrypt_report, verify_account
from cybermind.analyst.stage_evidence import analyze_stage_evidence, annotate_forecast_stage_coverage
from cybermind.analyst.view import compare_isolations, forecast_rows, input_shift_summary, load_uploaded_session, select_uploaded_sequence

ROOT = Path(__file__).resolve().parents[3]
app = FastAPI(title="CYBERMIND Analyst API", docs_url=None, redoc_url=None)
_sessions = {}
_lock = RLock()
MAX_UPLOAD_BYTES = 512 * 1024 * 1024

class Password(BaseModel):
    password: str

class Question(BaseModel):
    question: str

class Hosts(BaseModel):
    hosts: list[int]

class OpenCase(BaseModel):
    password: str
    payload: str

def _checkpoint():
    return Path(os.environ.get("CYBERMIND_CHECKPOINT", ROOT / "checkpoints/final_grouped/best.pt"))

def _json(value):
    return json.loads(json.dumps(value, default=str, allow_nan=False))

def _auth(authorization: str | None = Header(default=None)):
    token = authorization.removeprefix("Bearer ") if authorization else ""
    with _lock:
        session = _sessions.get(token)
    if session is None:
        raise HTTPException(401, "Unlock the local analyst console first.")
    return session

def _current(session):
    if session.get("capture") is None:
        raise HTTPException(409, "Load a PCAP or CSV capture first.")
    try:
        return select_uploaded_sequence(session["capture"], session["position"])
    except IndexError:
        raise HTTPException(400, "Replay window is out of range.")

@app.get("/api/status")
def status():
    from cybermind.models.graph_encoder import HAS_PYG, PYG_IMPORT_ERROR
    return {"account_ready": account_path().is_file(), "checkpoint_ready": _checkpoint().is_file(), "offline": True, "graph_backend": "torch_geometric" if HAS_PYG else "fallback", "graph_backend_error": PYG_IMPORT_ERROR}

@app.post("/api/auth/setup")
def setup(request: Password):
    try:
        create_account(account_path(), request.password)
    except FileExistsError:
        raise HTTPException(409, "A local account already exists.")
    except ValueError as error:
        raise HTTPException(400, str(error))
    return login(request)

@app.post("/api/auth/login")
def login(request: Password):
    if not verify_account(account_path(), request.password):
        raise HTTPException(401, "Login failed.")
    token = secrets.token_urlsafe(32)
    with _lock:
        _sessions[token] = {"capture": None, "position": -1, "report": None}
    return {"token": token}

@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None), session: dict = Depends(_auth)):
    with _lock:
        _sessions.pop(authorization.removeprefix("Bearer "), None)
    return {"ok": True}


def _demo_root() -> Path:
    return Path(os.environ.get("CYBERMIND_DEMOS_DIR", ROOT / "examples/analyst_demo")).resolve()

def _demos() -> dict[str, dict]:
    root = _demo_root()
    try:
        entries = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    result = {}
    for entry in entries:
        name = entry.get("file", "")
        path = (root / name).resolve()
        if (entry.get("synthetic") is True and name.endswith(".pcap")
                and path.is_relative_to(root) and path.is_file()):
            result[entry["id"]] = {**entry, "path": path}
    return result

@app.get("/api/demos")
def list_demos(session: dict = Depends(_auth)):
    return [{key: value for key, value in entry.items() if key != "path"}
            for entry in _demos().values()]

@app.get("/api/demos/{demo_id}/file")
def download_demo(demo_id: str, session: dict = Depends(_auth)):
    entry = _demos().get(demo_id)
    if entry is None:
        raise HTTPException(404, "Unknown demo capture.")
    if hashlib.sha256(entry["path"].read_bytes()).hexdigest() != entry["sha256"]:
        raise HTTPException(409, "Demo capture hash mismatch.")
    return FileResponse(entry["path"], media_type="application/vnd.tcpdump.pcap",
                        filename=entry["file"])

@app.post("/api/demos/{demo_id}/load")
def load_demo(demo_id: str, session: dict = Depends(_auth)):
    entry = _demos().get(demo_id)
    if entry is None:
        raise HTTPException(404, "Unknown demo capture.")
    if not _checkpoint().is_file():
        raise HTTPException(503, "The trusted checkpoint is unavailable.")
    if hashlib.sha256(entry["path"].read_bytes()).hexdigest() != entry["sha256"]:
        raise HTTPException(409, "Demo capture hash mismatch.")
    try:
        capture = load_uploaded_session(_checkpoint(), entry["path"])
    except (ValueError, KeyError) as error:
        raise HTTPException(422, str(error))
    capture[3].update(dataset=entry["file"], source="SYNTHETIC_DEMO",
                      demo_synthetic=True, demo_id=demo_id)
    session.update(capture=capture, position=len(capture[2]) - 1, report=None)
    return {"filename": entry["file"], "sequences": len(capture[2]),
            "input_sha256": capture[3]["dataset_sha256"],
            "packet_feature_coverage": capture[3]["packet_feature_coverage"],
            "synthetic": True, "demo_id": demo_id}

@app.post("/api/capture")
def load_capture(file: UploadFile = File(...), session: dict = Depends(_auth)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pcap", ".pcapng", ".csv"}:
        raise HTTPException(400, "Input must be PCAP, PCAPNG, or CSV.")
    if not _checkpoint().is_file():
        raise HTTPException(503, "The trusted checkpoint is unavailable.")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as stream:
            temporary = Path(stream.name)
            total = 0
            while chunk := file.file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Capture exceeds the 512 MiB local upload limit.")
                stream.write(chunk)
        capture = load_uploaded_session(_checkpoint(), temporary)
        capture[3]["dataset"] = Path(file.filename).name
        capture[3]["uploaded_filename"] = Path(file.filename).name
        session.update(capture=capture, position=len(capture[2])-1, report=None)
        return {"filename": Path(file.filename).name, "sequences": len(capture[2]),
                "input_sha256": capture[3]["dataset_sha256"],
                "packet_feature_coverage": capture[3]["packet_feature_coverage"]}
    except (ValueError, KeyError) as error:
        raise HTTPException(422, str(error))
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        file.file.close()

@app.get("/api/capture/forecast")
def forecast(position: int | None = Query(default=None), session: dict = Depends(_auth)):
    if position is not None:
        session["position"] = position
    model, cfg, sample, lineage, count = _current(session)
    observed = sample.states
    k = int(cfg["eval"]["rollout_steps"])
    draws = int(cfg["eval"].get("n_rollouts", 16))
    seed = int(cfg["eval"].get("rollout_seed", 0))
    with torch.no_grad():
        output = model.forecast(observed, k, n_rollouts=draws, seed=seed, explain=False)
    rows = forecast_rows(output, model, observed[-1].timestamp, sample.window_seconds)
    checkpoint = torch.load(_checkpoint(), map_location="cpu", weights_only=False)
    evidence = analyze_stage_evidence(observed, checkpoint.get("normalization"), rows[-1]["risk"])
    rows = annotate_forecast_stage_coverage(rows, evidence)
    flows = sample.metadata.get("observed_flow_rows", [])
    shift = input_shift_summary(observed)
    report = _json({"format": "CYBERMIND-REPORT-v1", "lineage": lineage,
                    "forecast": rows, "observed_flows": flows, "stage_evidence": evidence,
                    "input_shift": shift, "interventions": [], "explanation": None,
                    "seed": seed, "n_rollouts": draws,
                    "interpretation": "Model forecast for analyst review; no causal or autonomous-response claim."})
    session["report"] = report
    state = observed[-1]
    edges = [[int(a), int(b)] for a, b in state.edge_index.cpu().t().tolist() if a < 80 and b < 80]
    return _json({"position": lineage["sequence_index"], "sequences": count, "forecast": rows,
                  "stage_evidence": evidence, "flows": flows, "input_shift": shift,
                  "lineage": lineage, "network": {"hosts": list(state.node_ids[:80]), "edges": edges},
                  "flagged_flows": sum(bool(row.get("review_flag")) for row in flows),
                  "window_start": state.metadata.get("window_start")})

@app.post("/api/capture/explain")
def explain(session: dict = Depends(_auth)):
    model, cfg, sample, _, _ = _current(session)
    with torch.no_grad():
        result = model.forecast(sample.states, int(cfg["eval"]["rollout_steps"]),
                                n_rollouts=int(cfg["eval"].get("n_rollouts", 16)),
                                seed=int(cfg["eval"].get("rollout_seed", 0)))["explanation"]
    explanation = _json(result)
    if session.get("report") is not None:
        session["report"]["explanation"] = explanation
    return {"explanation": explanation, "limitation": "Attention and perturbations are not causal explanations."}

@app.post("/api/capture/isolate")
def isolate(request: Hosts, session: dict = Depends(_auth)):
    model, cfg, sample, _, _ = _current(session)
    if len(request.hosts) > 12 or len(set(request.hosts)) != len(request.hosts):
        raise HTTPException(400, "Select up to 12 distinct hosts.")
    try:
        rows = compare_isolations(model, sample.states, request.hosts,
                                  int(cfg["eval"]["rollout_steps"]),
                                  int(cfg["eval"].get("n_rollouts", 16)),
                                  int(cfg["eval"].get("rollout_seed", 0)))
    except ValueError as error:
        raise HTTPException(400, str(error))
    if session.get("report") is not None:
        session["report"]["interventions"] = _json(rows)
    return {"rows": _json(rows), "limitation": "Model-space sensitivity only; no isolation action is executed."}

@app.post("/api/capture/ask")
def ask(request: Question, session: dict = Depends(_auth)):
    if session.get("report") is None:
        raise HTTPException(409, "Run a forecast first.")
    _, _, sample, _, _ = _current(session)
    return answer_case_question(request.question, session["report"], sample.states)

@app.post("/api/case/seal")
def seal(request: Password, session: dict = Depends(_auth)):
    if not verify_account(account_path(), request.password):
        raise HTTPException(401, "Login verification failed.")
    if session.get("report") is None:
        raise HTTPException(409, "Run a forecast first.")
    payload = encrypt_report(session["report"], request.password)
    return Response(payload, media_type="application/octet-stream",
                    headers={"Content-Disposition": "attachment; filename=cybermind_case.cmcase"})

@app.post("/api/case/open")
def open_case(request: OpenCase, session: dict = Depends(_auth)):
    if not verify_account(account_path(), request.password):
        raise HTTPException(401, "Login verification failed.")
    try:
        report = decrypt_report(request.payload.encode("utf-8"), request.password)
    except ValueError as error:
        raise HTTPException(400, str(error))
    return {"report": report}

@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    dist = Path(os.environ.get("CYBERMIND_WEB_DIST", ROOT / "web/dist")).resolve()
    target = (dist / path).resolve()
    if path and target.is_file() and target.is_relative_to(dist):
        return FileResponse(target)
    index = dist / "index.html"
    if not index.is_file():
        raise HTTPException(503, "React assets are missing. Run npm run build in web/.")
    return FileResponse(index)

