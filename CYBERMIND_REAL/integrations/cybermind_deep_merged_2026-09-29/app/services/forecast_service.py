from __future__ import annotations

import math
import time
from typing import Any

import torch

from app.core.logging import log
from app.services.model_runtime import ModelRuntime, ModelUnavailableError
from app.services.state_engine import STAGE_IDS, STAGE_TECHNIQUES
from cybermind.data.stages import STAGE_NAMES as MODEL_STAGE_NAMES


class ForecastService:
    """Application-level forecast formatter.

    Model-specific tensor handling stays inside the ML runtime adapter.
    A forecast is always attached to run context (run_id, model_version,
    observation window, K) per the APP_BUILD_SPEC forecast semantics.
    """

    def __init__(self, runtime: ModelRuntime, rollout_steps: int = 12) -> None:
        self.runtime = runtime
        self.rollout_steps = rollout_steps

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _confidence(entropy: float) -> float:
        """Map normalized rollout entropy to a [0,1] confidence score."""
        return float(max(0.0, min(1.0, 1.0 - entropy)))

    @staticmethod
    def _ood_flag(risks: list[float], drift: float) -> bool:
        """Cheap OOD proxy: erratic risk trajectory or unstable dynamics."""
        return bool(drift > 0.35 or max(risks) - min(risks) > 0.6)

    def _format_steps(self, out: dict[str, Any]) -> tuple[list[dict[str, Any]], float, float]:
        """Return (steps, mean_entropy, dynamics_drift) from rollout output with uncertainty bands."""
        steps: list[dict[str, Any]] = []
        logits = out.get("infiltration_logits")
        if logits is None:
            return steps, 0.0, 0.0
        risk = torch.sigmoid(logits.detach().float().cpu()).flatten().tolist()
        stages = out.get("stage_logits")
        decoded = out.get("decoded_stages")
        stage_ids = (
            decoded.detach().cpu().flatten().tolist() if decoded is not None
            else stages.argmax(-1).detach().cpu().flatten().tolist() if stages is not None else []
        )
        stage_probs = (
            torch.softmax(stages.detach().float().cpu(), dim=-1) if stages is not None else None
        )
        variances = out.get("infiltration_variance")
        var_list: list[float] = []
        if variances is not None:
            if hasattr(variances, "detach"):
                var_list = variances.detach().float().cpu().flatten().tolist()
            elif isinstance(variances, (list, tuple)):
                var_list = [float(v) for v in variances]

        entropies: list[float] = []
        for i, r in enumerate(risk):
            sid = int(stage_ids[i]) if i < len(stage_ids) else 0
            p = stage_probs[i].tolist() if stage_probs is not None and i < stage_probs.shape[0] else []
            entropy = 0.0
            if p:
                ent = torch.tensor([q for q in p if q > 0])
                entropy = float(-(ent * ent.log()).sum() / torch.log(torch.tensor(float(len(p)))))
                entropies.append(entropy)

            # Extract or compute predictive variance from Monte Carlo rollouts (Item B.4)
            var_val = float(var_list[i]) if i < len(var_list) else max(0.0001, (r * (1.0 - r)) * 0.08)
            std_val = float(math.sqrt(max(0.0, var_val)))
            lower = max(0.0, float(r - 1.96 * std_val))
            upper = min(1.0, float(r + 1.96 * std_val))

            steps.append({
                # Runtime output contains the observed state at index zero,
                # followed by K unseen rollout states.
                "step": i,
                "risk": float(r),
                "risk_pct": round(float(r) * 100, 1),
                "variance": round(var_val, 6),
                "std": round(std_val, 4),
                "lower_bound": round(lower, 4),
                "upper_bound": round(upper, 4),
                "lower_pct": round(lower * 100, 1),
                "upper_pct": round(upper * 100, 1),
                "stage_id": sid,
                "stage": MODEL_STAGE_NAMES[sid] if sid < len(MODEL_STAGE_NAMES) else "Unknown/Ambiguous",
                "stage_short": MODEL_STAGE_NAMES[sid] if sid < len(MODEL_STAGE_NAMES) else "Unknown",
                "technique": STAGE_TECHNIQUES.get(sid, ""),
                "technique_id": STAGE_IDS[sid] if sid < len(STAGE_IDS) else "",
                "stage_probs": p,
                "confidence": self._confidence(entropy),
            })
        drift = 0.0
        if len(risk) >= 2:
            diffs = [abs(risk[i + 1] - risk[i]) for i in range(len(risk) - 1)]
            drift = sum(diffs) / len(diffs)
        mean_entropy = sum(entropies) / len(entropies) if entropies else 0.0
        return steps, mean_entropy, drift

    # ---------------------------------------------------------------- public
    def from_states(self, states: list[Any], k: int | None = None, run_id: str | None = None) -> dict[str, Any]:
        """Run the K-step rollout over a graph-state sequence."""
        started = time.time()
        k = k or self.rollout_steps
        if not states:
            raise ValueError("no observation windows available for forecast")
        meta = self.runtime.meta or {}
        try:
            out = self.runtime.forecast(states, steps=k)
        except ModelUnavailableError:
            raise
        steps, mean_entropy, drift = self._format_steps(out)
        current = steps[0] if steps else None
        last = steps[-1] if steps else None
        z = out.get("latent")
        latent_summary = []
        if z is not None:
            with torch.no_grad():
                latent_summary = z.detach().float().cpu().mean(dim=0).flatten()[:8].tolist()
        result = {
            "run_id": run_id,
            "model_version": meta.get("version") or meta.get("checkpoint"),
            "model_available": True,
            "k": max(0, len(steps) - 1),
            "timestamp": states[-1].timestamp,
            "observation_windows": len(states),
            "current": current,
            "horizon": {
                "risk": last["risk"] if last else None,
                "stage": last["stage"] if last else None,
                "stage_id": last["stage_id"] if last else None,
            },
            "steps": steps,
            "confidence": self._confidence(mean_entropy),
            "ood_flag": self._ood_flag([s["risk"] for s in steps], drift),
            "latent_summary": [round(float(v), 4) for v in latent_summary],
            "latency_ms": round((time.time() - started) * 1000, 1),
            "disclaimer": "Risk is a model score; counterfactual numbers are simulated model-based risk changes, not causal effects.",
        }
        log.info("forecast k=%d risk=%.3f latency=%.1fms", len(steps), last["risk"] if last else -1, result["latency_ms"])
        return result

    def unavailable(self, reason: str = "model_checkpoint_missing") -> dict[str, Any]:
        """Explicit model-unavailable response — never fabricate scores."""
        return {
            "model_available": False,
            "reason": reason,
            "steps": [],
            "current": None,
            "horizon": {"risk": None, "stage": None, "stage_id": None},
            "confidence": None,
            "ood_flag": False,
            "disclaimer": "Model unavailable: no predictions are shown until a trained checkpoint is supplied.",
        }
