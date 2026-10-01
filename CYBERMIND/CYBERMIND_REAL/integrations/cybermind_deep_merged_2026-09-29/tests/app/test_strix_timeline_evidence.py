from __future__ import annotations

import pytest

from app.services.strix_timeline_evidence import compare_sandbox_stage_evidence


def _forecast() -> dict:
    return {
        "forecast_id": "frozen-1",
        "forecast_ts": 1000.0,
        "model_version": "best.pt",
        "steps": [
            {"step": 1, "stage_id": 5, "stage": "Exfiltration", "risk": 0.1},
            {"step": 2, "stage_id": 3, "stage": "Lateral Movement", "risk": 0.4},
            {"step": 3, "stage_id": 4, "stage": "Command & Control", "risk": 0.6},
            {"step": 4, "stage_id": 5, "stage": "Exfiltration", "risk": 0.8},
            {"step": 5, "stage_id": 5, "stage": "Exfiltration", "risk": 0.9},
        ],
    }


def _event(stage: int, timestamp: float, event_id: str) -> dict:
    return {
        "event_id": event_id,
        "source": "sandbox_event_log",
        "stage_id": stage,
        "timestamp": timestamp,
        "evidence_ref": f"sha256:{event_id}",
        "verified_by": "sandbox-reviewer",
    }


def test_verified_events_match_only_their_future_time_windows():
    events = [_event(3, 1020.0, "lateral"), _event(5, 1070.0, "exfil")]
    events[1]["strix_finding_ids"] = ["finding-1"]
    result = compare_sandbox_stage_evidence(
        _forecast(), {"run_id": "strix-1", "status": "completed_findings"},
        {"findings": [{"finding_id": "finding-1", "timestamp": 1065.0}]},
        events, step_seconds=30.0,
    )
    lateral, exfil = result["stages"]
    assert (lateral["verdict"], lateral["model_prediction"]["step"]) == ("MATCH", 2)
    assert (exfil["verdict"], exfil["model_prediction"]["step"]) == ("MATCH", 4)
    assert exfil["strix_support"][0]["role"] == "supporting_heuristic_evidence_only"
    assert result["metric_status"] == "case_evidence_only_not_held_out_stage_accuracy"


def test_strix_finding_alone_never_becomes_ground_truth():
    result = compare_sandbox_stage_evidence(
        _forecast(), {"run_id": "strix-1"},
        {"observed_stage": 3, "findings": [{"finding_id": "finding-1", "attack_stage_hypothesis": 3}]},
        [], step_seconds=30.0,
    )
    assert all(s["verdict"] == "NO_VERIFIED_EVENT" for s in result["stages"])
    assert all(s["verified_observation"] is None for s in result["stages"])


def test_incomplete_or_past_event_cannot_make_a_match():
    unverified = _event(3, 1020.0, "missing-review")
    unverified.pop("verified_by")
    result = compare_sandbox_stage_evidence(
        _forecast(), {}, {}, [unverified, _event(5, 990.0, "past")], step_seconds=30.0,
    )
    assert result["stages"][0]["verdict"] == "NO_VERIFIED_EVENT"
    assert result["stages"][1]["verdict"] == "EVENT_OUTSIDE_HORIZON"


def test_wrong_stage_at_event_window_is_mismatch_even_if_another_step_matches():
    result = compare_sandbox_stage_evidence(
        _forecast(), {}, {}, [_event(3, 1040.0, "lateral")], step_seconds=30.0,
    )
    assert result["stages"][0]["verdict"] == "MISMATCH"
    assert result["stages"][0]["model_prediction"]["step"] == 3


def test_invalid_forecast_timing_is_rejected():
    with pytest.raises(ValueError, match="step_seconds"):
        compare_sandbox_stage_evidence(_forecast(), {}, {}, [], step_seconds=0)
    with pytest.raises(ValueError, match="forecast_ts"):
        compare_sandbox_stage_evidence({"steps": _forecast()["steps"]}, {}, {}, [], step_seconds=30)


def test_api_compares_linked_frozen_forecast_without_running_strix(monkeypatch):
    from fastapi.testclient import TestClient
    from app.api import routes
    from app.adapters.strix.schemas import EnvironmentClass, TargetRegistration
    from app.main import app

    forecast = _forecast()
    monkeypatch.setattr(routes, "forecast_history", [forecast])
    monkeypatch.setattr(routes.validation, "get_comparison", lambda _: {
        "validation_id": "validation-1", "forecast_id": "frozen-1",
        "strix_run_id": "strix-1", "scenario_id": "lateral_movement",
    })
    monkeypatch.setattr(routes.strix_runner, "get_run", lambda _: {
        "run_id": "strix-1", "status": "completed", "started_at": 1001.0,
        "target": "http://127.0.0.1:8081",
    })
    monkeypatch.setattr(routes.strix_runner.gate, "get", lambda _: TargetRegistration(
        target="http://127.0.0.1:8081", environment=EnvironmentClass.SANDBOX,
    ))
    monkeypatch.setattr(routes.strix_runner, "get_parsed", lambda _: {"findings": []})
    monkeypatch.setattr(routes.experiments, "create_run", lambda **_: {"run_id": "abc123"})
    monkeypatch.setattr(routes.experiments, "append_prediction", lambda *_: None)
    monkeypatch.setattr(routes.experiments, "close_run", lambda *_, **__: None)

    with TestClient(app) as client:
        response = client.post("/api/validations/validation-1/stage-evidence", json={
            "events": [_event(3, 1020.0, "lateral")],
        })
    assert response.status_code == 200
    assert response.json()["experiment_id"] == "abc123"
    assert response.json()["stages"][0]["verdict"] == "MATCH"
    assert response.json()["stages"][1]["verdict"] == "NO_VERIFIED_EVENT"


def test_forecast_created_after_strix_started_is_rejected():
    with pytest.raises(ValueError, match="before the Strix run"):
        compare_sandbox_stage_evidence(
            _forecast(), {"started_at": 999.0}, {}, [_event(3, 1020.0, "lateral")],
            step_seconds=30.0,
        )


def test_legacy_strix_keyword_stage_is_not_counted_as_model_stage_match():
    from app.services.validation_service import ValidationService

    service = object.__new__(ValidationService)
    comparison = service._build_comparison(
        scenario_id="lateral_movement",
        run={"run_id": "strix-1", "started_at": 1010.0, "finished_at": 1020.0},
        parsed={"observed_stage": 3, "findings": [{"severity": "high"}]},
        prediction={"stage_id": 3, "risk": 0.8},
        forecast_id="frozen-1",
        forecast_ts=1000.0,
    )
    assert comparison.match == "INCONCLUSIVE"
    assert comparison.observed_stage_inferred is True
    assert comparison.lead_time == 10.0
