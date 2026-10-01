from __future__ import annotations

import asyncio

import httpx
import pytest

from app.adapters.strix.safety import AuthorizationError, SafetyGate
from app.services.attack_lab_service import AttackLabService
from app.services.patch_service import PatchService
from app.services.state_engine import StateEngine, StateEngineConfig
from app.services.telemetry_service import TelemetryService

SANDBOX = "http://127.0.0.1:8081"


def _make_lab() -> AttackLabService:
    gate = SafetyGate()
    gate.register(SANDBOX, "SANDBOX")
    return AttackLabService(
        gate=gate,
        telemetry=TelemetryService(),
        state_engine=StateEngine(StateEngineConfig()),
        patch_service=PatchService(),
    )


def _run(coro):
    return asyncio.run(coro)


async def _reset_sandbox():
    async with httpx.AsyncClient(timeout=2.0) as client:
        res = await client.post(f"{SANDBOX}/sandbox/reset")
        assert res.status_code == 200


def test_probe_requires_registered_sandbox_target():
    """Unregistered targets must be hard-blocked by the safety gate."""

    async def _run_async():
        service = AttackLabService(
            gate=SafetyGate(),
            telemetry=TelemetryService(),
            state_engine=StateEngine(StateEngineConfig()),
            patch_service=PatchService(),
        )
        with pytest.raises(AuthorizationError) as ei:
            await service.start_probe(vector_id="ssh_bruteforce", intensity=3)
        assert ei.value.code in ("TARGET_NOT_REGISTERED", "AUTONOMOUS_NOT_SANDBOX")
        assert service.current_session is None

    _run(_run_async())


def test_unknown_vector_rejected():
    async def _run_async():
        lab = _make_lab()
        res = await lab.start_probe(vector_id="does_not_exist", intensity=3)
        assert "error" in res

    _run(_run_async())


def test_attack_lab_real_probe_verdict_and_one_click_patch():
    """Full loop against the REAL bundled sandbox on 127.0.0.1:8081.

    Verdicts come from actual HTTP responses:
    - unpatched: probes succeed -> VECTOR_SUCCEEDED + generated patch
    - one-click apply activates defence in sandbox + re-probe verification
    - patched: probes blocked -> PROBE_DEFLECTED
    """

    async def _run_async():
        await _reset_sandbox()
        lab = _make_lab()

        # 1. Status + vectors
        status = lab.get_status()
        assert status["environment"] == "SANDBOX (ISOLATED)"
        assert status["safety_gate"] == "ENFORCED (NON-EXPLOITING)"
        assert status["sandbox_online"] is True
        vectors = lab.list_available_vectors()
        assert len(vectors) >= 4
        assert any(v["id"] == "ssh_bruteforce" for v in vectors)

        # 2. Real probe: verdict must derive from actual sandbox responses.
        # (ssh_bruteforce runs its realistic 12-step depth regardless of intensity.)
        session = await lab.start_probe(vector_id="ssh_bruteforce", scan_mode="quick", intensity=12)
        assert session["session_id"].startswith("strix-probe-")
        await lab._task

        assert session["status"] == "VECTOR_SUCCEEDED", session.get("outcome_message")
        assert session["summary"]["succeeded"] == 12
        assert all(r["http_status"] == 401 for r in session["probe_records"])
        assert len(session["findings"]) == 1
        assert session["findings"][0]["cwe"].startswith("CWE-307")

        # 3. AI patch generated with unified diff + structured report
        patch = session["generated_patch"]
        assert patch is not None
        assert patch["patch_id"].startswith("patch-")
        assert patch["engine"] == "codebuff" or patch["engine"].startswith("ollama:")
        assert "--- a/" in patch["patch_diff"] and "+++ b/" in patch["patch_diff"]
        assert patch["what_happened"] and len(patch["what_to_do"]) >= 3

        # 4. ONE-CLICK APPLY: activates defence in sandbox + verification re-probe.
        apply_res = await lab.apply_one_click_patch(patch["patch_id"])
        assert apply_res["sandbox_active"] is True
        verification = apply_res["verification"]
        assert verification["verified"] is True
        assert verification["succeeded"] == 0
        assert verification["blocked"] >= 5
        assert apply_res["status"] == "APPLIED_AND_VERIFIED"

        # 5. Re-probe the patched target: every probe must be BLOCKED for real.
        reprobe = await lab.start_probe(vector_id="ssh_bruteforce", scan_mode="quick", intensity=12)
        await lab._task
        assert reprobe["status"] == "PROBE_DEFLECTED", reprobe.get("outcome_message")
        assert reprobe["summary"]["blocked"] == 12
        assert len(reprobe["findings"]) == 0

    _run(_run_async())


def test_all_four_vectors_round_trip():
    """Each of the 4 lab vectors: real probe succeeds -> patch -> verified closed."""

    async def _run_async():
        await _reset_sandbox()
        lab = _make_lab()

        for vector_id in ("sqli_probe", "smb_lateral", "c2_beacon"):
            session = await lab.start_probe(vector_id=vector_id, intensity=3)
            await lab._task
            assert session["status"] == "VECTOR_SUCCEEDED", (vector_id, session.get("outcome_message"))
            patch = session["generated_patch"]
            assert patch is not None, vector_id
            apply_res = await lab.apply_one_click_patch(patch["patch_id"])
            assert apply_res["verification"]["verified"] is True, (vector_id, apply_res.get("verification"))

            reprobe = await lab.start_probe(vector_id=vector_id, intensity=3)
            await lab._task
            assert reprobe["status"] == "PROBE_DEFLECTED", (vector_id, reprobe.get("outcome_message"))

    _run(_run_async())


def test_patch_verification_fails_when_sandbox_offline(monkeypatch):
    """If the sandbox is unreachable during apply, verification must FAIL loudly
    instead of pretending the patch worked."""

    async def _run_async():
        lab = AttackLabService(
            gate=SafetyGate(),
            telemetry=TelemetryService(),
            state_engine=StateEngine(StateEngineConfig()),
            patch_service=PatchService(),
        )
        patch_record = {
            "patch_id": "patch-fake0001",
            "vector_id": "ssh_bruteforce",
            "target": SANDBOX,
            "target_ip": "192.0.2.10",
            "target_port": 22,
            "applied": False,
        }
        lab.patch_service._patches["patch-fake0001"] = patch_record

        monkeypatch.setattr(
            "app.services.attack_lab_service.SANDBOX_BASE", "http://127.0.0.1:59999"
        )
        res = await lab.apply_one_click_patch("patch-fake0001")
        assert res["sandbox_active"] is False
        assert res["activation_error"] is not None
        assert res["status"] == "APPLIED_VERIFY_FAILED"
        assert res["verification"]["verified"] is False

    _run(_run_async())
