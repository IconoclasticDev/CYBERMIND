from __future__ import annotations

"""Neutral schemas for Strix integration.

Strix is the *controlled adversarial validation layer*: it produces evidence
from authorized, isolated runs. These schemas normalize that evidence into
CYBERMIND-neutral structures. Nothing here feeds the CYBERMIND prediction
path — predictions remain the world model's job.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EnvironmentClass(StrEnum):
    """Explicit authorization classification for a validation target."""

    SANDBOX = "SANDBOX"                # isolated local docker/synthetic environment
    REPLAY = "REPLAY"                  # recorded replay environment
    AUTHORIZED_TEST = "AUTHORIZED_TEST"  # explicitly registered test asset


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_FINDINGS = "completed_findings"  # exit 2: vulnerabilities found
    STOPPED = "stopped"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ExecutionMode(StrEnum):
    CLI = "cli"        # local strix binary (STRIX_BIN)
    DOCKER = "docker"  # strix sandboxed inside a docker container
    UNAVAILABLE = "unavailable"


@dataclass
class TargetRegistration:
    """A registered, authorized validation target. Registration is required
    before any Strix execution; unregistered targets are hard-blocked."""

    target: str                      # exact target string allowed (url/host/dir)
    environment: EnvironmentClass
    label: str = ""
    registered_at: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "environment": self.environment.value,
            "label": self.label,
            "registered_at": self.registered_at,
            "notes": self.notes,
        }


@dataclass
class StrixRunConfig:
    scenario_id: str
    target: str
    instruction: str
    scan_mode: str = "quick"          # quick | standard | deep
    max_budget: float | None = None   # USD cap passed via --max-budget
    timeout: float | None = None      # hard wall-clock cap enforced by the runner
    execution_mode: ExecutionMode = ExecutionMode.CLI

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "target": self.target,
            "instruction": self.instruction,
            "scan_mode": self.scan_mode,
            "max_budget": self.max_budget,
            "timeout": self.timeout,
            "execution_mode": self.execution_mode.value,
        }


@dataclass
class StrixRunRecord:
    run_id: str
    scenario_id: str
    started_at: float
    status: RunStatus = RunStatus.PENDING
    finished_at: float | None = None
    target: str = ""
    mode: str = "cli"
    budget: float | None = None
    artifacts_path: str | None = None
    return_code: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status.value,
            "target": self.target,
            "mode": self.mode,
            "budget": self.budget,
            "artifacts_path": self.artifacts_path,
            "return_code": self.return_code,
            "error": self.error,
        }


@dataclass
class NormalizedFinding:
    """A Strix finding translated into CYBERMIND-neutral evidence."""

    finding_id: str
    title: str
    severity: str                     # critical | high | medium | low | info
    cvss: float | None
    affected_asset: str | None        # endpoint/host the finding concerns
    evidence: str                     # poc/description summary
    reproduction_summary: str
    remediation_guidance: str
    confidence: float                 # evidence confidence in [0,1]
    timestamp: float | None
    cve: str | None = None
    cwe: str | None = None
    attack_stage_hypothesis: int | None = None   # CYBERMIND stage id, inferred
    attack_stage_inferred: bool = False           # ALWAYS true when hypothesis set
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "title": self.title,
            "severity": self.severity,
            "cvss": self.cvss,
            "affected_asset": self.affected_asset,
            "evidence": self.evidence,
            "reproduction_summary": self.reproduction_summary,
            "remediation_guidance": self.remediation_guidance,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "cve": self.cve,
            "cwe": self.cwe,
            "attack_stage_hypothesis": self.attack_stage_hypothesis,
            "attack_stage_inferred": self.attack_stage_inferred,
        }


@dataclass
class ValidationComparison:
    """Predicted (CYBERMIND) vs observed (Strix evidence) outcome."""

    validation_id: str
    scenario_id: str
    strix_run_id: str
    forecast_id: str | None
    predicted_stage: int | None
    predicted_stage_label: str | None
    predicted_risk: float | None
    predicted_entities: list[str] = field(default_factory=list)
    observed_stage: int | None = None
    observed_stage_label: str | None = None
    observed_stage_inferred: bool = True
    observed_risk_estimate: float | None = None
    observed_entities: list[str] = field(default_factory=list)
    finding_count: int = 0
    max_severity: str | None = None
    prediction_error: float | None = None   # |predicted_risk - observed_risk|
    match: str | None = None                # MATCH | PARTIAL | MISMATCH | INCONCLUSIVE
    lead_time: float | None = None          # forecast ts -> observed ts (seconds)
    started_at: float = 0.0
    finished_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "scenario_id": self.scenario_id,
            "strix_run_id": self.strix_run_id,
            "forecast_id": self.forecast_id,
            "predicted_stage": self.predicted_stage,
            "predicted_stage_label": self.predicted_stage_label,
            "predicted_risk": self.predicted_risk,
            "predicted_entities": self.predicted_entities,
            "observed_stage": self.observed_stage,
            "observed_stage_label": self.observed_stage_label,
            "observed_stage_inferred": self.observed_stage_inferred,
            "observed_risk_estimate": self.observed_risk_estimate,
            "observed_entities": self.observed_entities,
            "finding_count": self.finding_count,
            "max_severity": self.max_severity,
            "prediction_error": self.prediction_error,
            "match": self.match,
            "lead_time": self.lead_time,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }
