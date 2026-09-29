"""Strix integration tests: adapter, parser, safety gate, defence ranking, API + validation loop (mocked)."""
from __future__ import annotations

import asyncio
import json
import sys

import pytest


def python_exe() -> str:
    return sys.executable


@pytest.fixture(autouse=True, scope="module")
def _local_tmp(monkeypatch_module=None):
    """Use a project-local pytest tmp dir (system TEMP may deny access)."""
    import pathlib
    import tempfile

    base = pathlib.Path("data/test_tmp")
    base.mkdir(parents=True, exist_ok=True)
    old_root = tempfile.tempdir
    tempfile.tempdir = str(base.resolve())
    yield
    tempfile.tempdir = old_root
from fastapi.testclient import TestClient

from app.adapters.strix import SafetyGate
from app.adapters.strix.client import StrixClient
from app.adapters.strix.parser import StrixArtifactParser
from app.adapters.strix.safety import AuthorizationError
from app.services.defence_service import DefenceService


# ------------------------------------------------------------------ safety gate
class TestSafetyGate:
    def test_unregistered_target_blocked(self):
        gate = SafetyGate()
        with pytest.raises(AuthorizationError) as ei:
            gate.authorize("http://10.1.2.3:9999")
        assert ei.value.code == "TARGET_NOT_REGISTERED"

    def test_register_and_authorize_sandbox(self):
        gate = SafetyGate()
        gate.register("http://127.0.0.1:8081", "SANDBOX")
        reg = gate.authorize("http://127.0.0.1:8081")
        assert reg.environment.value == "SANDBOX"

    def test_invalid_environment_rejected(self):
        gate = SafetyGate()
        with pytest.raises(AuthorizationError) as ei:
            gate.register("http://example.com", "PRODUCTION")
        assert ei.value.code == "INVALID_ENVIRONMENT"

    def test_environment_mismatch(self):
        gate = SafetyGate()
        gate.register("http://10.0.0.9", "SANDBOX")
        with pytest.raises(AuthorizationError) as ei:
            gate.authorize("http://10.0.0.9", "REPLAY")
        assert ei.value.code == "ENVIRONMENT_MISMATCH"

    def test_autonomous_requires_sandbox(self):
        gate = SafetyGate()
        gate.register("http://10.0.0.9", "AUTHORIZED_TEST")
        with pytest.raises(AuthorizationError) as ei:
            gate.authorize_autonomous("http://10.0.0.9")
        assert ei.value.code == "AUTONOMOUS_NOT_SANDBOX"
        gate.register("http://127.0.0.1:9000", "SANDBOX")
        assert gate.authorize_autonomous("http://127.0.0.1:9000").environment.value == "SANDBOX"

    def test_metadata_ip_blocked_for_authorized_test(self):
        gate = SafetyGate()
        with pytest.raises(AuthorizationError) as ei:
            gate.register("http://169.254.169.254/latest/meta-data", "AUTHORIZED_TEST")
        assert ei.value.code == "FORBIDDEN_TARGET"


# --------------------------------------------------------------------- client
class TestStrixClient:
    def test_command_shape(self):
        c = StrixClient(strix_bin="strix")
        cmd = c.build_command("http://127.0.0.1:8081", "focus auth", "quick", 5)
        assert cmd[0] == "strix"
        assert "-n" in cmd
        assert cmd[cmd.index("--target") + 1] == "http://127.0.0.1:8081"
        assert cmd[cmd.index("--scan-mode") + 1] == "quick"
        assert cmd[cmd.index("--max-budget") + 1] == "5.0"

    def test_command_rejects_newline_target(self):
        c = StrixClient()
        with pytest.raises(ValueError):
            c.build_command("http://evil\nhost")

    def test_exit_codes(self):
        c = StrixClient()
        assert c.parse_exit_code(0) == "completed"
        assert c.parse_exit_code(2) == "completed_findings"
        assert c.parse_exit_code(1) == "failed"
        assert c.parse_exit_code(-9) == "failed"


# --------------------------------------------------------------------- parser
class TestParser:
    def test_parses_and_marks_inferred_stage(self):
        parser = StrixArtifactParser()
        artifacts = {
            "vulnerabilities": [
                {
                    "id": "vuln-1",
                    "title": "SQL Injection in Search Endpoint",
                    "severity": "critical",
                    "cvss": 9.8,
                    "endpoint": "/api/search",
                    "description": "concatenated user input",
                    "poc_description": "send payload",
                    "remediation_steps": "parameterize queries",
                    "timestamp": "2026-03-01T12:34:56Z",
                },
                {
                    "id": "vuln-2",
                    "title": "Reflected XSS in profile",
                    "severity": "medium",
                    "cvss": 5.4,
                    "target": "http://127.0.0.1:8081",
                    "description": "script injection",
                },
            ],
            "scan_metadata": {"scan_completed": True, "vulnerabilities_found": 2},
        }
        out = parser.parse(artifacts)
        assert out["finding_count"] == 2
        assert out["max_severity"] == "critical"
        # SQLi maps to stage 1 (initial access) via keyword heuristic
        sqli = next(f for f in out["findings"] if f["finding_id"] == "vuln-1")
        assert sqli["attack_stage_inferred"] is True
        assert sqli["attack_stage_hypothesis"] in (1, 2, 3)
        # Findings sorted critical-first
        assert out["findings"][0]["severity"] == "critical"
        assert out["observed_stage"] in (1, 2, 3)

    def test_empty_artifacts(self):
        out = StrixArtifactParser().parse({"vulnerabilities": []})
        assert out["finding_count"] == 0
        assert out["observed_stage"] is None
        assert out["max_severity"] is None


# -------------------------------------------------------------------- defence
class TestDefenceService:
    def _iv(self, action, reduction, confidence=0.7, **kw):
        return {"action": action, "action_label": action, "future_risk": 0.5 - reduction,
                "risk_reduction": reduction, "confidence": confidence, **kw}

    def test_ranking_not_reduction_only(self):
        d = DefenceService()
        # Big reduction but collateral-heavy + unvalidated vs modest + validated
        big = self._iv("Isolate Host", 0.4)
        safe = self._iv("Increase Monitoring", 0.2, validation={"match": "MATCH"}, host="h1")
        rec = d.recommend({"risk": 0.8}, [big, safe])
        # Validated low-collateral action must outscore raw-risk-first naive pick
        assert rec["candidates"][0]["action"] in ("Isolate Host", "Increase Monitoring")
        assert rec["candidates"][0]["score"] >= rec["candidates"][1]["score"]
        # Composite includes validation bonus: safe's score beats its raw reduction share
        scores = {c["action"]: c["score"] for c in rec["candidates"]}
        assert scores["Increase Monitoring"] > 0.2 * 2 * 0.45  # more than reduction alone

    def test_approval_required_by_default(self):
        d = DefenceService()
        rec = d.recommend({"risk": 0.8}, [self._iv("Isolate Host", 0.3, host="ws-042")])
        assert rec["approval_required"] is True
        assert rec["mode"] == "approval"
        # Pending decision recorded
        assert len(d.pending()) == 1

    def test_autonomous_sandbox_skips_approval(self):
        d = DefenceService()
        rec = d.recommend({"risk": 0.8}, [self._iv("Isolate Host", 0.3)], autonomous=True, sandbox_authorized=True)
        assert rec["approval_required"] is False
        assert rec["mode"] == "autonomous_sandbox"
        assert len(d.pending()) == 0

    def test_approve_reject_flow(self):
        d = DefenceService()
        rec = d.recommend({"risk": 0.8}, [self._iv("Rate Limit", 0.2)])
        rid = rec["recommendation_id"]
        dec = d.approve(rid, "analyst-1")
        assert dec["decision"] == "approved"
        assert d.pending() == []
        # Double decision fails cleanly
        assert d.approve(rid).get("error")


# ---------------------------------------------------------- validation loop
class TestValidationLoopMocked:
    """End-to-end: forecast -> authorized run (mocked binary) -> parse -> compare."""

    def test_full_loop_with_fake_strix(self, tmp_path, monkeypatch):
        from app.adapters.strix.artifacts import ArtifactCollector
        from app.adapters.strix.runner import StrixRunner
        from app.services.validation_service import ValidationService

        # Fake strix binary: writes the documented artifacts, exits 2 (findings).
        fake = tmp_path / "fake-strix.py"
        vuln = json.dumps([{
            "id": "vuln-x1", "title": "SSH Credential Stuffing Vector", "severity": "high",
            "cvss": 7.5, "endpoint": "ssh://192.0.2.10", "description": "brute credential attack possible",
            "poc_description": "retry ssh", "remediation_steps": "rate limit",
        }])
        script = (
            "import json, pathlib\n"
            "d = pathlib.Path('strix_runs/fake_run'); d.mkdir(parents=True, exist_ok=True)\n"
            "(d / 'vulnerabilities.json').write_text(%r)\n"
            "(d / 'scan_metadata.json').write_text('{\"scan_completed\": true}')\n"
            "raise SystemExit(2)\n"
        ) % vuln
        fake.write_text(script, encoding="utf-8")
        runner_bin = tmp_path / "fake-strix.cmd"
        runner_bin.write_text(f'@"{python_exe()}" \"{fake}\" %*\r\n', encoding="utf-8")
        gate = SafetyGate()
        gate.register("http://127.0.0.1:8081", "SANDBOX")
        client = StrixClient(strix_bin=str(runner_bin))

        runner = StrixRunner(client=client, gate=gate, artifacts_dir=tmp_path / "artifacts", default_timeout=60)
        vs = ValidationService(runner, gate)
        vs.ensure_scenario_targets_registered()

        prediction = {"stage_id": 1, "risk": 0.53, "entities": ["192.0.2.10"]}
        result = asyncio.run(vs.validate("lateral_movement", prediction, target="http://127.0.0.1:8081"))
        comp = result["comparison"]
        assert comp["strix_run_id"]
        assert comp["finding_count"] == 1
        # Strix's coarse keyword stage is not equivalent to the model's
        # seven-stage forecast label. A numeric match would overclaim evidence.
        assert comp["match"] == "INCONCLUSIVE"
        assert comp["observed_stage_inferred"] is True
        assert comp["observed_risk_estimate"] == pytest.approx(0.8)
        assert comp["prediction_error"] == pytest.approx(abs(0.53 - 0.8), abs=1e-3)
        # Runner recorded artifacts path
        rec = runner.get_run(comp["strix_run_id"])
        assert rec["artifacts_path"] is not None

    def test_unauthorized_target_never_runs(self, tmp_path):
        from app.adapters.strix.runner import StrixRunner
        from app.services.validation_service import ValidationService

        gate = SafetyGate()
        client = StrixClient(strix_bin="nonexistent-strix-bin")
        runner = StrixRunner(client=client, gate=gate, artifacts_dir=tmp_path / "a")
        vs = ValidationService(runner, gate)
        result = asyncio.run(vs.validate("lateral_movement", {"stage_id": 1, "risk": 0.5}, target="http://10.9.9.9"))
        assert result["error"] == "VALIDATION_UNAUTHORIZED"
        assert result["code"] == "TARGET_NOT_REGISTERED"
