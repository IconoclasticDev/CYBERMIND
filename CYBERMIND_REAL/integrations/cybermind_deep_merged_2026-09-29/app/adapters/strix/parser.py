from __future__ import annotations

"""Parse Strix artifacts into CYBERMIND-neutral schemas.

Strix findings are vulnerability evidence, NOT attack-stage ground truth. The
stage hypothesis below is an *inferred* heuristic (CWE/title keyword based)
and every such mapping is flagged `attack_stage_inferred: True`.
"""

import re
import time
from typing import Any

from app.adapters.strix.schemas import NormalizedFinding

# Heuristic mapping from Strix finding text/CWE to CYBERMIND research stage ids
# (0 BENIGN, 1 RECON/INITIAL ACCESS, 2 EXECUTION/LATERAL, 3 IMPACT/EXFIL).
# Explicitly a hypothesis generator, not ATT&CK ground truth.
_STAGE_KEYWORDS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (3, ("exfil", "data breach", "mass assignment", "deserialization", "rce")),
    (2, ("lateral", "ssrf", "idor", "privilege", "auth bypass", "access control", "session", "jwt")),
    (1, ("injection", "sql", "xss", "command inject", "ssti", "xxe", "credential", "brute")),
)

_SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
_SEVERITY_TO_CONFIDENCE = {"critical": 0.95, "high": 0.9, "medium": 0.75, "low": 0.6, "info": 0.4}


def _infer_stage(text: str) -> tuple[int | None, bool]:
    low = text.lower()
    for stage, keywords in _STAGE_KEYWORDS:
        for kw in keywords:
            if kw in low:
                return stage, True
    return None, False


def _parse_ts(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        from datetime import datetime

        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except Exception:  # noqa: BLE001
        return None


class StrixArtifactParser:
    """vulnerabilities.json + scan_metadata.json -> NormalizedFinding list + summary."""

    def parse(self, artifacts: dict[str, Any]) -> dict[str, Any]:
        raw_vulns = artifacts.get("vulnerabilities") or []
        meta = artifacts.get("scan_metadata") or {}
        findings: list[NormalizedFinding] = []
        for i, v in enumerate(raw_vulns):
            if not isinstance(v, dict):
                continue
            title = str(v.get("title") or f"finding-{i}")
            text_blob = " ".join(
                str(v.get(k) or "") for k in ("title", "description", "technical_analysis", "impact", "cwe")
            )
            stage, inferred = _infer_stage(text_blob)
            sev = str(v.get("severity") or "info").lower()
            findings.append(NormalizedFinding(
                finding_id=str(v.get("id") or f"finding-{i}"),
                title=title,
                severity=sev if sev in _SEVERITY_RANK else "info",
                cvss=_as_float(v.get("cvss")),
                affected_asset=str(v.get("endpoint") or v.get("target") or "") or None,
                evidence=str(v.get("poc_description") or v.get("description") or ""),
                reproduction_summary=str(v.get("poc_description") or ""),
                remediation_guidance=str(v.get("remediation_steps") or ""),
                confidence=_SEVERITY_TO_CONFIDENCE.get(sev, 0.5),
                timestamp=_parse_ts(v.get("timestamp")),
                cve=v.get("cve"),
                cwe=v.get("cwe"),
                attack_stage_hypothesis=stage,
                attack_stage_inferred=inferred,
                raw={k: v.get(k) for k in ("cvss_breakdown", "code_locations", "method") if v.get(k)},
            ))
        findings.sort(key=lambda f: _SEVERITY_RANK.get(f.severity, 0), reverse=True)
        max_sev = findings[0].severity if findings else None
        observed_stage: int | None = None
        if findings:
            # Observed stage = highest stage hypothesized from real evidence.
            stages = [f.attack_stage_hypothesis for f in findings if f.attack_stage_hypothesis is not None]
            observed_stage = max(stages) if stages else None
        return {
            "findings": [f.to_dict() for f in findings],
            "finding_count": len(findings),
            "max_severity": max_sev,
            "max_cvss": max((f.cvss or 0.0) for f in findings) if findings else None,
            "observed_stage": observed_stage,
            "observed_stage_inferred": observed_stage is not None,
            "scan_metadata": meta,
            "parsed_at": time.time(),
        }


def _as_float(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None
