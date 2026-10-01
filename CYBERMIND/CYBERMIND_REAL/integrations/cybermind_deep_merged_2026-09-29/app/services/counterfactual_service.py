from __future__ import annotations

import time
from typing import Any

import torch

from cybermind.counterfactual.simulator import Intervention, mutate_state

from app.core.logging import log
from app.services.model_runtime import ModelRuntime, ModelUnavailableError
from cybermind.data.stages import STAGE_NAMES as MODEL_STAGE_NAMES

ACTION_LABELS = {
    "No Action": "No action (baseline)",
    "Block Host": "Block host",
    "Block Port": "Block port",
    "Isolate Host": "Isolate host",
    "Restrict Edge": "Restrict edge",
    "Rate Limit": "Rate limit",
}
RISK_BANDS = [(0.25, "LOW"), (0.5, "MEDIUM"), (0.75, "HIGH"), (1.01, "CRITICAL")]


def risk_band(risk: float) -> str:
    for threshold, band in RISK_BANDS:
        if risk < threshold:
            return band
    return "CRITICAL"


class CounterfactualService:
    """Baseline future vs intervened future, using the same trained model.

    Semantics per APP_BUILD_SPEC: clone the graph/window in memory, apply a
    permitted intervention, run the same model. Never mutate live state and
    never claim causal effects — output is simulated/model-based risk change.
    """

    def __init__(self, runtime: ModelRuntime) -> None:
        self.runtime = runtime

    # ------------------------------------------------------------------ core
    def _rollout_risk(self, state: Any, k: int) -> tuple[float, list[float], int, list[int]]:
        """Final risk, full risk trajectory, final stage id, per-step stage ids."""
        out = self.runtime.forecast([state], steps=k)
        logits = out.get("infiltration_logits")
        if logits is None:
            return 0.0, [], 0, []
        risks = torch.sigmoid(logits.detach().float().cpu()).flatten().tolist()
        stages = out.get("stage_logits")
        decoded = out.get("decoded_stages")
        stage_ids = (
            decoded.detach().cpu().flatten().tolist() if decoded is not None
            else stages.argmax(-1).detach().cpu().flatten().tolist() if stages is not None else []
        )
        final_stage = int(stage_ids[-1]) if stage_ids else 0
        return float(risks[-1]), risks, final_stage, [int(s) for s in stage_ids]

    def _interventions(
        self,
        state: Any,
        action: str,
        host: str | None,
        port: int | None,
        edge: list[int] | None,
    ) -> list[dict[str, Any]]:
        """Build concrete intervention candidates from a UI request."""
        candidates: list[dict[str, Any]] = []
        node_ids = list(state.node_ids)
        if action in ("auto", "all"):
            candidates.append({"action": "No Action"})
            for i, nid in enumerate(node_ids):
                candidates.append({"action": "Isolate Host", "host": nid, "host_index": i})
            if port is not None:
                candidates.append({"action": "Block Port", "port": int(port)})
            candidates.append({"action": "Rate Limit"})
        else:
            cand: dict[str, Any] = {"action": action}
            if host is not None:
                if host not in node_ids:
                    raise ValueError(f"unknown host: {host}")
                cand["host"] = host
                cand["host_index"] = node_ids.index(host)
            if port is not None:
                cand["port"] = int(port)
            if edge is not None:
                cand["edge"] = [int(edge[0]), int(edge[1])]
            candidates.append(cand)
        return candidates

    def _apply(self, state: Any, cand: dict[str, Any]) -> Any:
        iv = Intervention(
            action=cand["action"],
            host=cand.get("host_index"),
            port=cand.get("port"),
            edge=tuple(cand["edge"]) if cand.get("edge") else None,
        )
        return mutate_state(state, iv)

    # ---------------------------------------------------------------- public
    def simulate(
        self,
        state: Any,
        action: str = "auto",
        host: str | None = None,
        port: int | None = None,
        edge: list[int] | None = None,
        k: int = 6,
    ) -> dict[str, Any]:
        started = time.time()
        base_risk, base_traj, base_stage, base_stages = self._rollout_risk(state, k)
        results: list[dict[str, Any]] = []
        for cand in self._interventions(state, action, host, port, edge):
            try:
                mutated = self._apply(state, cand)
                r, traj, stage, stages = self._rollout_risk(mutated, k)
            except Exception as exc:  # noqa: BLE001
                log.warning("intervention failed: %s %s", cand.get("action"), exc)
                continue
            results.append({
                "action": cand["action"],
                "action_label": ACTION_LABELS.get(cand["action"], cand["action"]),
                "host": cand.get("host"),
                "port": cand.get("port"),
                "edge": cand.get("edge"),
                "future_risk": round(r, 4),
                "risk_delta": round(r - base_risk, 4),
                "risk_reduction": round(base_risk - r, 4),
                "band": risk_band(r),
                "trajectory": [round(v, 4) for v in traj],
                "stage": MODEL_STAGE_NAMES[stage] if stage < len(MODEL_STAGE_NAMES) else "Unknown/Ambiguous",
                "stage_short": MODEL_STAGE_NAMES[stage] if stage < len(MODEL_STAGE_NAMES) else "Unknown",
                "stage_ids": stages,
            })
        results.sort(key=lambda x: x["future_risk"])
        # A recommendation must beat the baseline by a visible margin; a
        # numerically tied or harmful intervention is only a simulation result.
        best = next(
            (r for r in results if r["action"] != "No Action" and r["risk_reduction"] >= 0.001),
            None,
        )
        baseline_entry = next((r for r in results if r["action"] == "No Action"), None)
        return {
            "model_available": True,
            "k": k,
            "timestamp": state.timestamp,
            "baseline": {
                "risk": round(base_risk, 4),
                "band": risk_band(base_risk),
                "trajectory": [round(v, 4) for v in base_traj],
                "stage": MODEL_STAGE_NAMES[base_stage] if base_stage < len(MODEL_STAGE_NAMES) else "Unknown/Ambiguous",
                "stage_short": MODEL_STAGE_NAMES[base_stage] if base_stage < len(MODEL_STAGE_NAMES) else "Unknown",
                "stage_ids": base_stages,
            },
            "interventions": results,
            "recommended": best,
            "baseline_entry": baseline_entry,
            "latency_ms": round((time.time() - started) * 1000, 1),
            "disclaimer": (
                "Counterfactual Risk Simulation: model-based risk comparison between simulated futures. "
                "Not a causal effect estimate."
            ),
        }

    # --------------------------------------------------------- attack gravity
    def attack_gravity(self, state: Any, k: int = 6) -> dict[str, Any]:
        """Per-host gravity: baseline risk minus isolate-host counterfactual risk."""
        started = time.time()
        base_risk, base_traj, _, _ = self._rollout_risk(state, k)
        rows: list[dict[str, Any]] = []
        for i, nid in enumerate(state.node_ids):
            try:
                mutated = self._apply(state, {"action": "Isolate Host", "host": nid, "host_index": i})
                r, _, _, _ = self._rollout_risk(mutated, k)
            except Exception as exc:  # noqa: BLE001
                log.warning("gravity failed for %s: %s", nid, exc)
                continue
            rows.append({
                "host": nid,
                "index": i,
                "baseline_risk": round(base_risk, 4),
                "counterfactual_risk": round(r, 4),
                "attack_gravity": round(base_risk - r, 4),
            })
        rows.sort(key=lambda x: x["attack_gravity"], reverse=True)
        top = rows[0] if rows else None
        return {
            "model_available": True,
            "k": k,
            "timestamp": state.timestamp,
            "baseline_risk": round(base_risk, 4),
            "baseline_trajectory": [round(v, 4) for v in base_traj],
            "gravity": rows,
            "critical_asset": top,
            "latency_ms": round((time.time() - started) * 1000, 1),
            "disclaimer": (
                "Attack Gravity = P(future compromise | current state) - "
                "P(future compromise | isolate host), model-based simulation."
            ),
        }
