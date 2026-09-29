from __future__ import annotations

"""Defence Recommendation Engine.

Ranks candidate interventions (from the counterfactual service) using
predicted risk reduction, model confidence, Strix validation evidence,
collateral impact and reversibility. Emits approval requirements for
consequential actions; nothing here executes anything.
"""

import time
import uuid
from typing import Any

from app.core.logging import log

# Reversibility/impact scoring per intervention type (0-1, higher = safer to apply).
_REVERSIBILITY = {
    "No Action": 1.0,
    "Increase Monitoring": 0.95,
    "Rate Limit": 0.9,
    "Block Port": 0.7,
    "Restrict Edge": 0.6,
    "Block Host": 0.5,
    "Isolate Host": 0.35,
}
_COLLATERAL = {
    "No Action": 0.0,
    "Increase Monitoring": 0.05,
    "Rate Limit": 0.15,
    "Block Port": 0.35,
    "Restrict Edge": 0.4,
    "Block Host": 0.55,
    "Isolate Host": 0.8,
}


class DefenceService:
    """Predict -> Simulate -> Validate -> Defend ranking layer."""

    def __init__(self) -> None:
        self._pending: dict[str, dict[str, Any]] = {}
        self._decisions: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------ ranking
    @staticmethod
    def score(rec: dict[str, Any], validation: dict[str, Any] | None) -> float:
        """Composite score in [0,1]: weighted reduction/confidence/validation/
        collateral/reversibility. Deliberately NOT reduction-only."""
        reduction = max(0.0, float(rec.get("risk_reduction") or 0.0))
        confidence = float(rec.get("confidence") or 0.5)
        action = rec.get("action") or ""
        rev = _REVERSIBILITY.get(action, 0.5)
        coll = _COLLATERAL.get(action, 0.5)
        val_bonus = 0.0
        if validation:
            if validation.get("match") in ("MATCH", "PARTIAL"):
                val_bonus = 0.15 if validation.get("match") == "MATCH" else 0.08
            elif validation.get("match") == "MISMATCH":
                val_bonus = -0.1
        score = (
            0.45 * min(reduction * 2, 1.0)   # risk reduction (saturating)
            + 0.2 * confidence
            + 0.15 * rev
            - 0.1 * coll
            + val_bonus
        )
        return max(0.0, min(score, 1.0))

    def recommend(
        self,
        baseline: dict[str, Any],
        interventions: list[dict[str, Any]],
        validations: dict[str, dict[str, Any]] | None = None,
        autonomous: bool = False,
        sandbox_authorized: bool = False,
    ) -> dict[str, Any]:
        """Build a ranked recommendation from counterfactual + validation inputs."""
        validations = validations or {}
        candidates = [iv for iv in interventions if iv.get("action") != "No Action"]
        ranked: list[dict[str, Any]] = []
        for iv in candidates:
            val = validations.get(self._validation_key(iv))
            s = self.score(iv, val)
            ranked.append({
                **iv,
                "confidence": round(min(0.99, float(iv.get("confidence") or 0.7) + (0.1 if val else 0.0)), 3),
                "validation": val,
                "validated": bool(val and val.get("match") in ("MATCH", "PARTIAL")),
                "reversibility": _REVERSIBILITY.get(iv.get("action") or "", 0.5),
                "collateral_impact": _COLLATERAL.get(iv.get("action") or "", 0.5),
                "score": round(s, 4),
            })
        ranked.sort(key=lambda x: x["score"], reverse=True)
        best = ranked[0] if ranked else None
        recommendation_id = uuid.uuid4().hex[:12]
        approval_required = not (autonomous and sandbox_authorized)
        out = {
            "recommendation_id": recommendation_id,
            "action": best["action"] if best else None,
            "action_label": best.get("action_label") if best else None,
            "host": best.get("host") if best else None,
            "port": best.get("port") if best else None,
            "reason": (
                f"Highest composite score ({best['score']:.2f}) balancing predicted risk "
                f"reduction, model confidence, reversibility and validation evidence."
                if best else "No positive-intervention candidates available."
            ),
            "baseline_risk": round(float(baseline.get("risk") or 0.0) * 100),
            "expected_risk": round(float(best.get("future_risk") or 0.0) * 100) if best else None,
            "risk_delta": round(-float(best.get("risk_reduction") or 0.0) * 100) if best else None,
            "confidence": best.get("confidence") if best else None,
            "validated": bool(best and best.get("validated")),
            "validation_run_id": (((best or {}).get("validation") or {}).get("strix_run_id")) if best else None,
            "approval_required": approval_required,
            "mode": "autonomous_sandbox" if (autonomous and sandbox_authorized) else "approval",
            "candidates": ranked,
            "disclaimer": (
                "Recommendation ranks MODEL-SIMULATED futures; validation evidence comes from "
                "controlled Strix runs in authorized environments. Not causal proof."
            ),
            "generated_at": time.time(),
        }
        if approval_required and best is not None:
            self._pending[recommendation_id] = out
        return out

    @staticmethod
    def _validation_key(iv: dict[str, Any]) -> str:
        host = iv.get("host") or ""
        return f"{iv.get('action')}:{host}" if host else str(iv.get("action"))

    # ----------------------------------------------------------- approvals
    def approve(self, recommendation_id: str, approver: str = "analyst") -> dict[str, Any]:
        rec = self._pending.pop(recommendation_id, None)
        if rec is None:
            return {"error": "recommendation not found or already decided", "recommendation_id": recommendation_id}
        decision = {
            "recommendation_id": recommendation_id,
            "decision": "approved",
            "approver": approver,
            "action": rec.get("action"),
            "host": rec.get("host"),
            "port": rec.get("port"),
            "decided_at": time.time(),
        }
        self._decisions[recommendation_id] = decision
        log.info("defence recommendation %s approved by %s", recommendation_id, approver)
        return decision

    def reject(self, recommendation_id: str, approver: str = "analyst", reason: str = "") -> dict[str, Any]:
        rec = self._pending.pop(recommendation_id, None)
        if rec is None:
            return {"error": "recommendation not found or already decided", "recommendation_id": recommendation_id}
        decision = {
            "recommendation_id": recommendation_id,
            "decision": "rejected",
            "approver": approver,
            "reason": reason[:300],
            "decided_at": time.time(),
        }
        self._decisions[recommendation_id] = decision
        log.info("defence recommendation %s rejected by %s", recommendation_id, approver)
        return decision

    def pending(self) -> list[dict[str, Any]]:
        return list(self._pending.values())

    def get_decision(self, recommendation_id: str) -> dict[str, Any] | None:
        return self._decisions.get(recommendation_id)
