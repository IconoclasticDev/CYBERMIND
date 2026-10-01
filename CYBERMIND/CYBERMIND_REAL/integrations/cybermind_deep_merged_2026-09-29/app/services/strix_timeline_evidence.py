"""Backend-only comparison of a frozen forecast with verified sandbox events.

Strix findings support an investigation but do not establish that an attack
stage occurred. A MATCH requires an independently recorded, analyst-verified
sandbox event within the forecast horizon. Nothing here changes model output.
"""

from __future__ import annotations

import math
from typing import Any

from cybermind.data.stages import STAGE_NAMES


TARGET_STAGES = (3, 5)  # Lateral Movement, Exfiltration
PROTOCOL = "sandbox_stage_evidence_v1"


def _verified_event(event: dict[str, Any], stage_id: int) -> bool:
    """Only independent event-log records can act as observed stage labels."""
    return (
        event.get("stage_id") == stage_id
        and event.get("source") == "sandbox_event_log"
        and bool(event.get("event_id"))
        and bool(event.get("evidence_ref"))
        and bool(event.get("verified_by"))
        and isinstance(event.get("timestamp"), (int, float))
        and math.isfinite(event["timestamp"])
    )


def compare_sandbox_stage_evidence(
    forecast: dict[str, Any],
    strix_run: dict[str, Any],
    parsed_strix: dict[str, Any],
    sandbox_events: list[dict[str, Any]],
    *,
    step_seconds: float,
) -> dict[str, Any]:
    """Compare frozen K-step predictions with independently verified events.

    Forecast step 1 is the observed state; steps 2..K+1 are future windows.
    An event at t requires the matching prediction at ceil((t-t0)/stride),
    where t0 is the frozen forecast time. Strix findings never determine MATCH.
    """
    if not math.isfinite(step_seconds) or step_seconds <= 0:
        raise ValueError("step_seconds must be finite and positive")
    t0 = forecast.get("forecast_ts")
    if not isinstance(t0, (int, float)) or not math.isfinite(t0):
        raise ValueError("forecast_ts must be a finite frozen forecast timestamp")
    run_started = strix_run.get("started_at")
    if isinstance(run_started, (int, float)) and math.isfinite(run_started) and t0 >= run_started:
        raise ValueError("forecast must be frozen before the Strix run starts")
    future = sorted(
        (s for s in forecast.get("steps", []) if isinstance(s, dict) and isinstance(s.get("step"), int) and s["step"] >= 2),
        key=lambda s: s["step"],
    )
    if not future or [s["step"] for s in future] != list(range(2, len(future) + 2)):
        raise ValueError("forecast must contain consecutive future steps after observed step 1")

    horizon_seconds = len(future) * step_seconds
    findings = parsed_strix.get("findings") or []
    finding_by_id = {str(f.get("finding_id")): f for f in findings if f.get("finding_id")}
    stage_results = []
    for stage_id in TARGET_STAGES:
        verified = sorted(
            (e for e in sandbox_events if isinstance(e, dict) and _verified_event(e, stage_id)),
            key=lambda e: e["timestamp"],
        )
        in_horizon = [e for e in verified if t0 < e["timestamp"] <= t0 + horizon_seconds]
        event = in_horizon[0] if in_horizon else None
        if event is None:
            verdict = "NO_VERIFIED_EVENT" if not verified else "EVENT_OUTSIDE_HORIZON"
            predicted = None
            observed = None
            support = []
        else:
            horizon_step = min(len(future), math.ceil((event["timestamp"] - t0) / step_seconds))
            predicted = future[horizon_step - 1]
            verdict = "MATCH" if predicted.get("stage_id") == stage_id else "MISMATCH"
            observed = {
                "event_id": event["event_id"],
                "timestamp": event["timestamp"],
                "stage_id": stage_id,
                "stage": STAGE_NAMES[stage_id],
                "source": event["source"],
                "evidence_ref": event["evidence_ref"],
                "verified_by": event["verified_by"],
            }
            support = [
                {
                    "finding_id": str(fid),
                    "timestamp": finding_by_id[str(fid)].get("timestamp"),
                    "role": "supporting_heuristic_evidence_only",
                }
                for fid in (event.get("strix_finding_ids") or [])
                if str(fid) in finding_by_id
            ]
        stage_results.append({
            "stage_id": stage_id,
            "stage": STAGE_NAMES[stage_id],
            "verdict": verdict,
            "forecast_steps": [
                {"step": s["step"], "stage_id": s.get("stage_id"),
                 "stage": s.get("stage"), "risk": s.get("risk")}
                for s in future
            ],
            "model_prediction": None if predicted is None else {
                "step": predicted["step"],
                "stage_id": predicted.get("stage_id"),
                "stage": predicted.get("stage"),
                "risk": predicted.get("risk"),
                "source": "frozen_world_model_forecast",
            },
            "verified_observation": observed,
            "strix_support": support,
        })

    return {
        "protocol": PROTOCOL,
        "forecast_id": forecast.get("forecast_id"),
        "forecast_ts": t0,
        "model_version": forecast.get("model_version"),
        "strix_run_id": strix_run.get("run_id"),
        "strix_status": strix_run.get("status"),
        "step_seconds": step_seconds,
        "future_step_count": len(future),
        "stages": stage_results,
        "evidence_rule": "Strix findings are supporting heuristic evidence, never attack-stage ground truth.",
        "metric_status": "case_evidence_only_not_held_out_stage_accuracy",
    }
