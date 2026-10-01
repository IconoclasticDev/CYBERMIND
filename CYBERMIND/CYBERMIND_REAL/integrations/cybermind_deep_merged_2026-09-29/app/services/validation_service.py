from __future__ import annotations

"""Validation service: the Predict -> Simulate -> Validate -> Compare loop.

Runs a controlled Strix scan against a REGISTERED sandbox target for the
current scenario, then compares CYBERMIND's prediction (stage/risk) with the
observed evidence. Every comparison becomes a persisted experiment.
"""

import asyncio
import time
import uuid
from typing import Any

from app.adapters.strix import (
    AuthorizationError,
    EnvironmentClass,
    SafetyGate,
    StrixRunner,
)
from app.adapters.strix.schemas import StrixRunConfig, ValidationComparison
from app.core.logging import log
from app.services.state_engine import STAGE_NAMES, STAGE_SHORT
from cybermind.data.stages import STAGE_NAMES as MODEL_STAGE_NAMES

# Scenario id -> authorized default target + instruction for controlled validation.
SCENARIO_TARGETS: dict[str, dict[str, str]] = {
    "lateral_movement": {
        "target": "http://127.0.0.1:8081",
        "instruction": (
            "Authorized lab validation. Focus on SSH brute force, lateral SMB "
            "movement, and exfiltration staging paths. Quick validation scan."
        ),
    },
    "brute_force": {
        "target": "http://127.0.0.1:8081",
        "instruction": "Authorized lab validation. Focus on SSH credential brute force vectors only.",
    },
    "recon_heavy": {
        "target": "http://127.0.0.1:8081",
        "instruction": "Authorized lab validation. Focus on exposed service surface and information disclosure.",
    },
    "benign_baseline": {
        "target": "http://127.0.0.1:8081",
        "instruction": "Authorized lab validation. General quick sweep of the isolated sandbox target.",
    },
}

SEVERITY_TO_RISK = {"critical": 0.95, "high": 0.8, "medium": 0.55, "low": 0.3, "info": 0.1}


class ValidationService:
    """Orchestrates one validation cycle and stores the comparison."""

    def __init__(self, runner: StrixRunner, gate: SafetyGate) -> None:
        self.runner = runner
        self.gate = gate
        self.comparisons: dict[str, ValidationComparison] = {}
        self.runner.on_event(self._on_runner_event)

    # ------------------------------------------------------------ lifecycle
    def ensure_scenario_targets_registered(self) -> None:
        """Idempotently register the built-in SANDBOX validation targets."""
        for sid, cfg in SCENARIO_TARGETS.items():
            if self.gate.get(cfg["target"]) is None:
                self.gate.register(
                    target=cfg["target"],
                    environment=EnvironmentClass.SANDBOX,
                    label=f"Built-in sandbox target for scenario '{sid}'",
                    notes=f"Auto-registered for controlled validation of scenario {sid}",
                )

    def default_target_for(self, scenario_id: str) -> dict[str, str] | None:
        return SCENARIO_TARGETS.get(scenario_id)

    def _on_runner_event(self, event: str, payload: dict[str, Any]) -> None:
        # Hook for websocket fan-out; wired by the API layer.
        pass

    # ----------------------------------------------------------------- run
    async def validate(
        self,
        scenario_id: str,
        prediction: dict[str, Any],
        target: str | None = None,
        instruction: str | None = None,
        scan_mode: str = "quick",
        max_budget: float | None = None,
        forecast_id: str | None = None,
        forecast_ts: float | None = None,
    ) -> dict[str, Any]:
        """Run one authorized Strix validation + build the comparison record."""
        cfg = SCENARIO_TARGETS.get(scenario_id)
        use_target = target or (cfg or {}).get("target")
        use_instruction = instruction or (cfg or {}).get("instruction") or "Authorized validation scan."
        if not use_target:
            return {"error": "SCENARIO_FAILED", "detail": f"no registered validation target for scenario '{scenario_id}'"}

        try:
            run = await self.runner.start_run(StrixRunConfig(
                scenario_id=scenario_id,
                target=use_target,
                instruction=use_instruction,
                scan_mode=scan_mode,
                max_budget=max_budget,
            ))
        except AuthorizationError as exc:
            return {"error": "VALIDATION_UNAUTHORIZED", "code": exc.code, "detail": str(exc)}
        except RuntimeError as exc:
            return {"error": "VALIDATION_UNAVAILABLE", "detail": str(exc)}

        run_id = run["run_id"]
        # Await completion (runner enforces its own timeout as safety net).
        deadline = time.time() + 2400.0
        while time.time() < deadline:
            rec = self.runner.get_run(run_id) or {}
            if rec.get("finished_at") or rec.get("status") in ("failed", "timeout", "stopped"):
                break
            await asyncio.sleep(2.0)

        parsed = self.runner.get_parsed(run_id) or {}
        rec = self.runner.get_run(run_id) or {}
        comparison = self._build_comparison(
            scenario_id=scenario_id,
            run=rec,
            parsed=parsed,
            prediction=prediction,
            forecast_id=forecast_id,
            forecast_ts=forecast_ts,
        )
        self.comparisons[comparison.validation_id] = comparison
        return {"run": rec, "comparison": comparison.to_dict(), "parsed": parsed}

    # ----------------------------------------------------------- comparison
    def _build_comparison(
        self,
        scenario_id: str,
        run: dict[str, Any],
        parsed: dict[str, Any],
        prediction: dict[str, Any],
        forecast_id: str | None,
        forecast_ts: float | None,
    ) -> ValidationComparison:
        started = run.get("started_at") or time.time()
        finished = run.get("finished_at") or time.time()
        findings = parsed.get("findings") or []
        observed_stage = parsed.get("observed_stage")
        predicted_stage = prediction.get("stage_id")
        predicted_risk = prediction.get("risk")

        # Observed risk estimate from evidence severity (clearly labeled estimate).
        obs_risk = None
        if findings:
            severities = [f.get("severity") for f in findings]
            obs_risk = max((SEVERITY_TO_RISK.get(s, 0.2) for s in severities), default=None)

        # Entity overlap: findings' affected assets vs predicted entity list.
        predicted_entities = [str(e) for e in (prediction.get("entities") or [])]
        observed_entities = sorted({str(f.get("affected_asset")) for f in findings if f.get("affected_asset")})

        # Strix's coarse keyword stages are not the model's seven-stage label
        # space. A numeric equality here would be a false validation claim.
        # The separate sandbox event-log comparison handles exact stage/time.
        match = "INCONCLUSIVE"

        err = None
        if predicted_risk is not None and obs_risk is not None:
            err = round(abs(float(predicted_risk) - float(obs_risk)), 4)

        return ValidationComparison(
            validation_id=uuid.uuid4().hex[:12],
            scenario_id=scenario_id,
            strix_run_id=run.get("run_id") or "",
            forecast_id=forecast_id,
            predicted_stage=predicted_stage,
            predicted_stage_label=(MODEL_STAGE_NAMES[predicted_stage]
                                   if predicted_stage is not None and 0 <= predicted_stage < len(MODEL_STAGE_NAMES)
                                   else None),
            predicted_risk=predicted_risk,
            predicted_entities=predicted_entities,
            observed_stage=observed_stage,
            observed_stage_label=STAGE_NAMES.get(observed_stage) if observed_stage is not None else None,
            observed_stage_inferred=True,
            observed_risk_estimate=obs_risk,
            observed_entities=observed_entities,
            finding_count=len(findings),
            max_severity=parsed.get("max_severity"),
            prediction_error=err,
            match=match,
            lead_time=round(started - forecast_ts, 1) if forecast_ts else None,
            started_at=started,
            finished_at=finished,
        )

    # -------------------------------------------------------------- queries
    def list_comparisons(self, limit: int = 50) -> list[dict[str, Any]]:
        items = sorted(self.comparisons.values(), key=lambda c: c.started_at, reverse=True)[:limit]
        return [c.to_dict() for c in items]

    def get_comparison(self, validation_id: str) -> dict[str, Any] | None:
        c = self.comparisons.get(validation_id)
        return c.to_dict() if c else None
