"""Bounded, in-process checks against the bundled demonstration target.

These checks exercise actual target responses. They are not Strix findings,
independent attack labels, or evidence of model stage accuracy.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from typing import Any

import httpx


async def run_local_sandbox_validation(forecast: dict[str, Any]) -> dict[str, Any]:
    from sandbox.target_app import IN_PROCESS_VALIDATION, app as sandbox_app

    frozen = {
        "forecast_id": forecast.get("forecast_id"),
        "forecast_ts": forecast.get("forecast_ts"),
        "model_version": forecast.get("model_version"),
        "predicted_stage": (forecast.get("horizon") or {}).get("stage"),
        "predicted_risk": (forecast.get("horizon") or {}).get("risk"),
    }
    checks: list[dict[str, Any]] = []
    transport = httpx.ASGITransport(app=sandbox_app)
    token = IN_PROCESS_VALIDATION.set(True)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://bundled-sandbox", timeout=3.0) as client:
            probes = (
                ("sandbox health", "GET", "/sandbox/health", None),
                ("invalid login", "POST", "/api/vulnerable/auth", {"username": "cybermind_probe", "password": "invalid-probe-only"}),
                ("share access", "GET", "/api/vulnerable/smb", None),
                ("query handling", "POST", "/api/vulnerable/query", {"filter_param": "probe' OR 1=1 --"}),
            )
            for name, method, path, body in probes:
                try:
                    response = await client.request(method, path, json=body)
                    checks.append({
                        "name": name,
                        "http_status": response.status_code,
                        "response_sha256": hashlib.sha256(response.content).hexdigest(),
                        "outcome": "observed",
                    })
                except httpx.HTTPError as exc:
                    checks.append({"name": name, "http_status": None, "response_sha256": None,
                                   "outcome": "error", "error": type(exc).__name__})
            await asyncio.sleep(0)
    finally:
        IN_PROCESS_VALIDATION.reset(token)

    return {
        "run_id": f"local-{uuid.uuid4().hex[:12]}",
        "created_at": time.time(),
        "mode": "BUNDLED_IN_PROCESS_SANDBOX",
        "verdict": "SANDBOX_RESPONSES_OBSERVED" if all(c["outcome"] == "observed" for c in checks) else "INCONCLUSIVE",
        "forecast": frozen,
        "checks": checks,
        "limitation": (
            "This checks the bundled demonstration target's HTTP behavior. It does not run Strix, "
            "establish an independently verified attack stage, or measure model forecast accuracy."
        ),
    }
