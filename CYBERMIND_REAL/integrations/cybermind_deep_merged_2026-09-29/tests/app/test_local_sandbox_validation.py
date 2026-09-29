from __future__ import annotations

import asyncio
import pathlib
import tempfile
import time

import pytest

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.main import app
from app.services.local_sandbox_validation import run_local_sandbox_validation
from sandbox.target_app import PROBE_STATS


@pytest.fixture(autouse=True)
def _local_tmp(monkeypatch):
    """System TEMP may deny access on this machine; use a project-local tmp."""
    base = pathlib.Path("data/test_tmp")
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tempfile, "tempdir", str(base.resolve()))


def test_bundled_sandbox_check_records_real_responses_without_claiming_model_accuracy():
    flow_count_before = PROBE_STATS["flows_streamed"]
    result = asyncio.run(run_local_sandbox_validation({
        "forecast_id": "frozen-test-forecast",
        "forecast_ts": 123.0,
        "model_version": "test",
        "horizon": {"stage": "Benign", "risk": 0.2},
    }))

    assert result["mode"] == "BUNDLED_IN_PROCESS_SANDBOX"
    assert result["verdict"] == "SANDBOX_RESPONSES_OBSERVED"
    assert result["forecast"]["forecast_id"] == "frozen-test-forecast"
    assert [c["name"] for c in result["checks"]] == [
        "sandbox health", "invalid login", "share access", "query handling",
    ]
    assert [c["http_status"] for c in result["checks"]] == [200, 401, 200, 200]
    assert all(len(c["response_sha256"]) == 64 for c in result["checks"])
    assert "does not run Strix" in result["limitation"]
    assert "accuracy" in result["limitation"]
    assert PROBE_STATS["flows_streamed"] == flow_count_before


def test_local_validation_api_records_result_for_the_current_forecast(tmp_path, monkeypatch):
    monkeypatch.setattr(routes.experiments, "root", tmp_path)
    with TestClient(app) as client:
        now = time.time()
        events = [{
            "timestamp": now + i * 60,
            "src": "192.0.2.20", "dst": "192.0.2.10",
            "src_port": 40000 + i, "dst_port": 443, "protocol": 6,
            "bytes_fwd": 1000, "bytes_bwd": 500,
            "packets_fwd": 10, "packets_bwd": 5, "duration": 1.0,
        } for i in range(8)]
        assert client.post("/api/telemetry/events", json={"events": events}).status_code == 200
        forecast = client.get("/api/forecast/current")
        assert forecast.status_code == 200
        assert forecast.json().get("forecast_id")
        # A case remains locally testable even when no forecast page was opened.
        routes.forecast_history.clear()
        response = client.post("/api/validation/local")
        assert response.status_code == 200, response.text
        run = response.json()
        assert run["forecast"]["forecast_id"]
        assert run["forecast"]["forecast_id"] != forecast.json()["forecast_id"]
        assert run["verdict"] == "SANDBOX_RESPONSES_OBSERVED"
        assert client.get("/api/validation/local").json()["runs"][0]["run_id"] == run["run_id"]
