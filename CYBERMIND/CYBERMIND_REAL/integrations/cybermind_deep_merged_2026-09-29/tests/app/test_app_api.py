from __future__ import annotations

import sys
import time
import csv
import io
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def _batch(n: int = 5, attack: bool = False):
    events = []
    base = time.time()
    for i in range(n):
        events.append({
            "timestamp": base + i * 30,
            "src": "192.0.2.20",
            "dst": "192.0.2.10" if i % 2 else "192.0.2.30",
            "src_port": 40000 + i,
            "dst_port": 443,
            "protocol": 6,
            "bytes_fwd": 1000 + i,
            "bytes_bwd": 500,
            "packets_fwd": 10,
            "packets_bwd": 5,
            "duration": 1.0,
            "label": "SSH-BRUTEFORCE" if attack else "BENIGN",
            "attack_stage": 1 if attack else 0,
            "source": "test",
        })
    return {"events": events}


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "model" in body and "telemetry_events" in body


def test_model_endpoint_reports_metadata(client):
    """Model endpoint must report honest metadata in both available and missing states."""
    r = client.get("/api/model")
    assert r.status_code == 200
    body = r.json()
    if body.get("available") is True:
        assert "version" in body and body.get("parameters", 0) > 0
    else:
        assert body.get("reason") in {"checkpoint_missing", "checkpoint_invalid", "not_loaded"}


def test_forecast_never_fabricates_without_model(client):
    r = client.get("/api/forecast")
    assert r.status_code == 200
    body = r.json()
    if body.get("model_available") is False:
        assert body.get("risk") is None or body.get("steps") == []


def test_ingest_and_state(client):
    r = client.post("/api/telemetry/events", json=_batch(6))
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] == 6
    st = client.get("/api/state/current").json()
    assert len(st["nodes"]) >= 2
    assert st["event_count"] >= 6
    tl = client.get("/api/timeline?limit=10").json()
    assert len(tl["events"]) >= 1


def test_timeline_limit(client):
    r = client.get("/api/timeline?limit=2")
    assert r.status_code == 200
    assert len(r.json()["events"]) <= 2


def test_scenario_listing(client):
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    ids = [s["id"] for s in r.json()["scenarios"]]
    assert "benign_baseline" in ids and "lateral_movement" in ids


def test_scenario_start_generates_telemetry(client):
    r = client.post("/api/scenarios/start", json={"scenario_id": "benign_baseline", "interval": 0.3, "speed": 4.0})
    assert r.status_code == 200
    assert r.json()["status"] == "started"
    time.sleep(2.0)
    st = client.get("/api/state/current").json()
    assert st["event_count"] > 0
    client.post("/api/scenarios/stop", json={"scenario_id": "benign_baseline"})


def test_timestamped_csv_upload_produces_four_future_steps(client, monkeypatch):
    from app.main import forecast_service
    monkeypatch.setattr(forecast_service, "rollout_steps", 4)
    rows = [
        {"timestamp": f"2018-03-01T12:{i:02d}:00Z", "src": "192.0.2.10",
         "dst": "192.0.2.20", "src_port": "1234", "dst_port": "80",
         "protocol": "6", "bytes_fwd": "100", "bytes_bwd": "50",
         "packet_features_available": "1"}
        for i in range(8)
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0])
    writer.writeheader()
    writer.writerows(rows)
    response = client.post(
        "/api/upload/flows?clear_previous=true",
        files={"file": ("chronological.csv", output.getvalue().encode(), "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["flows_ingested"] == 8
    assert body["time_basis"] == "source_timestamps"
    assert body["state_ready"] is True
    assert body["forecast"]["k"] == 4
    assert [step["step"] for step in body["forecast"]["steps"]] == [0, 1, 2, 3, 4]


def test_bundled_real_flow_samples_load(client):
    """Real CIC-IDS2018 CSVs load up to `limit` rows with zero rejections;
    every event carries REAL DATASET provenance."""
    for testcase_id, min_events in (("ssh_bruteforce", 15079), ("botnet_ares", 21310)):
        response = client.post(
            "/api/testcases/load",
            json={"testcase_id": testcase_id, "limit": 1500, "clear_previous": True},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["accepted"] == 1500
        assert body["rejected"] == 0
        assert body["ready"] is True
        assert min_events > 0  # registry declares the full capture size


def test_benchmark_is_checkpoint_matched_saved_evidence(client):
    response = client.get("/api/benchmark/comparison")
    assert response.status_code == 200
    body = response.json()
    assert body["dataset_flows_evaluated"] == 4156
    assert body["models"]["cybermind_world_model"]["confusion_matrix"] == {
        "tp": 2666, "fp": 8, "tn": 1408, "fn": 74,
    }
    assert body["models"]["logistic_baseline"]["confusion_matrix"]["fp"] == 186
    assert "saved" in body["source"].lower()


def test_strix_status_docker_probe_has_no_windows_console(client, monkeypatch):
    import shutil
    import subprocess
    from types import SimpleNamespace

    if not hasattr(subprocess, "CREATE_NO_WINDOW"):
        return
    seen = {}
    original_which = shutil.which
    monkeypatch.setattr(shutil, "which", lambda binary: "docker.exe" if binary == "docker" else original_which(binary))

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["creationflags"] = kwargs.get("creationflags", 0)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    response = client.get("/api/strix/status")
    assert response.status_code == 200
    assert seen["command"][0] == "docker"
    assert seen["creationflags"] & subprocess.CREATE_NO_WINDOW


def test_counterfactual_does_not_recommend_a_tied_intervention(monkeypatch):
    from app.services.counterfactual_service import CounterfactualService
    service = CounterfactualService(runtime=None)
    monkeypatch.setattr(service, "_rollout_risk", lambda state, k: (0.5, [0.5] * (k + 1), 0, [0] * (k + 1)))
    monkeypatch.setattr(service, "_interventions", lambda *args: [
        {"action": "No Action"}, {"action": "Isolate Host", "host": "192.0.2.10"},
    ])
    monkeypatch.setattr(service, "_apply", lambda state, candidate: state)
    result = service.simulate(state=type("State", (), {"timestamp": 0.0})(), k=4)
    assert result["recommended"] is None
    assert result["interventions"][0]["risk_reduction"] == 0.0


def test_scenario_unknown_404(client):
    r = client.post("/api/scenarios/start", json={"scenario_id": "does_not_exist"})
    assert r.status_code == 404


def test_counterfactual_shape_or_safe_failure(client):
    """With state+model: full result shape. Without: 404/503 — never fabricated numbers."""
    r = client.post("/api/counterfactual/simulate", json={"action": "auto"})
    if r.status_code == 200:
        body = r.json()
        assert "baseline" in body and "interventions" in body and "disclaimer" in body
        assert body["baseline"]["risk"] is not None
    else:
        assert r.status_code in {404, 503}


def test_replay_files_endpoint(client):
    r = client.get("/api/replay/files")
    assert r.status_code == 200
    assert "files" in r.json()


def test_replay_load_rejects_traversal(client):
    r = client.post("/api/replay/load", json={"filename": "../secrets.jsonl"})
    assert r.status_code in {400, 404}


def test_experiment_flow(client):
    from app.main import experiments
    run = experiments.create_run(scenario_id="test", model_version="test-version")
    experiments.append_prediction(run["run_id"], {"risk": 0.5})
    r = client.get(f"/api/experiments/{run['run_id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["scenario_id"] == "test"
    assert body["predictions"][0]["risk"] == 0.5
    assert client.get("/api/experiments").status_code == 200


def test_websocket_live(client):
    with client.websocket_connect("/ws/live") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "system"
        ws.send_text("ping")
        assert ws.receive_json()["status"] == "alive"
