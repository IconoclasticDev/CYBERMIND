from __future__ import annotations

import hashlib
import time
from pathlib import Path
from dataclasses import replace
from typing import Any

import torch

from cybermind.models.world_model import WorldModel  # noqa: E402  (path set up by app/__init__)

from app.core.logging import log


class ModelUnavailableError(RuntimeError):
    """Raised when inference is requested but no trained checkpoint exists."""


class ModelRuntime:
    """Thin adapter around the existing CYBERMIND model.

    The app should depend on this interface rather than importing model internals
    throughout API routes. Load happens once per backend process; metadata and
    health are exposed without fabricating any score when unavailable.
    """

    def __init__(self, checkpoint: Path, device: str = "auto") -> None:
        self.checkpoint_path = checkpoint
        self.device = self._select_device(device)
        self.model: WorldModel | None = None
        self.normalizer = None
        self.meta: dict[str, Any] = {"available": False, "reason": "not_loaded"}
        self.loaded_at: float | None = None
        self.load_error: str | None = None

    @property
    def version(self) -> str:
        if not self.meta.get("available"):
            return "unavailable"
        if self.meta.get("version"):
            return str(self.meta["version"])
        step = self.meta.get("global_step")
        digest = hashlib.sha1(str(self.checkpoint_path).encode()).hexdigest()[:6]
        return f"cybermind-{digest}" + (f"-step{step}" if step is not None else "")

    @staticmethod
    def config_hash(meta: dict[str, Any]) -> str:
        payload = str(meta.get("model_config", {})) + str(meta.get("node_dim", ""))
        return hashlib.sha1(payload.encode()).hexdigest()[:10]

    @staticmethod
    def _select_device(requested: str) -> torch.device:
        if requested == "cpu":
            return torch.device("cpu")
        if requested in {"cuda", "auto"} and torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")

    def load(self) -> dict[str, Any]:
        if not self.checkpoint_path.exists():
            self.model = None
            self.meta = {
                "available": False,
                "reason": "checkpoint_missing",
                "expected_path": str(self.checkpoint_path),
                "message": "Place the trained model at models/cybermind_final.pt. No predictions will be fabricated.",
            }
            log.warning("model checkpoint missing at %s", self.checkpoint_path)
            return self.meta

        try:
            with self.checkpoint_path.open("rb") as checkpoint_file:
                checkpoint_sha256 = hashlib.file_digest(checkpoint_file, "sha256").hexdigest()
            ckpt = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)
            node_dim = int(ckpt["node_dim"])
            cfg = ckpt.get("config", {})
            model_cfg = cfg.get("model", {})

            from cybermind.data.normalization import FeatureNormalizer
            constants = ckpt.get("normalization")
            if cfg.get("data", {}).get("require_normalization") and constants is None:
                raise ValueError("Checkpoint requires training normalization but has none")
            normalizer = FeatureNormalizer(constants) if constants else None
            from cybermind.utils.config import edge_model_kwargs, stage_model_kwargs

            mc = model_cfg
            self.model = WorldModel(
                node_dim=node_dim,
                graph_hidden=int(mc.get("graph_hidden", 128)),
                graph_out=int(mc.get("graph_out", 128)),
                temporal_dim=int(mc.get("temporal_dim", 128)),
                nhead=int(mc.get("nhead", 4)),
                temporal_layers=int(mc.get("temporal_layers", 2)),
                num_stages=int(mc.get("num_stages", 7)),
                dropout=float(mc.get("dropout", 0.1)),
                graph_heads=int(mc.get("graph_heads", 4)),
                **edge_model_kwargs(mc),
                **stage_model_kwargs(cfg),
            ).to(self.device)
            self.model.load_state_dict(ckpt["model_state"])
            self.model.eval()
            self.normalizer = normalizer

            params = sum(p.numel() for p in self.model.parameters())
            self.meta = {
                "available": True,
                "checkpoint": str(self.checkpoint_path),
                "checkpoint_name": self.checkpoint_path.name,
                "device": str(self.device),
                "cuda_available": torch.cuda.is_available(),
                "node_dim": node_dim,
                "model_config": model_cfg,
                "global_step": ckpt.get("global_step"),
                "parameters": params,
                "checkpoint_sha256": checkpoint_sha256,
                "version": "cybermind-" + checkpoint_sha256[:12]
                + (f"-step{ckpt['global_step']}" if ckpt.get("global_step") is not None else ""),
                "config_hash": self.config_hash({"model_config": model_cfg, "node_dim": node_dim}),
                "loaded_at": time.time(),
            }
            self.loaded_at = time.time()
            self.load_error = None
            log.info("model loaded: %s (%d params, device=%s)", self.meta["checkpoint_name"], params, self.meta["device"])
        except Exception as exc:  # noqa: BLE001
            self.model = None
            self.normalizer = None
            self.load_error = str(exc)
            self.meta = {
                "available": False,
                "reason": "checkpoint_invalid",
                "expected_path": str(self.checkpoint_path),
                "error": str(exc),
                "message": "Checkpoint could not be validated/loaded. Fix the checkpoint; no predictions will be fabricated.",
            }
            log.error("model load failed: %s", exc)
        return self.meta

    def ensure_loaded(self) -> None:
        if self.model is None and self.meta.get("reason") not in ("checkpoint_missing", "checkpoint_invalid"):
            self.load()
        if self.model is None:
            raise ModelUnavailableError(self.meta.get("reason", "unavailable"))

    def health(self) -> dict[str, Any]:
        """Lightweight health probe without forcing a heavy load."""
        return {
            "available": bool(self.model is not None),
            "status": "loaded" if self.model is not None else self.meta.get("reason", "not_loaded"),
            "device": str(self.device),
            "version": self.version,
            "parameters": self.meta.get("parameters"),
            "checkpoint": str(self.checkpoint_path),
            "checkpoint_present": self.checkpoint_path.exists(),
            "load_error": self.load_error,
            "expected_path": str(self.checkpoint_path),
        }

    def _prepare_state(self, state):
        """Apply checkpoint training normalization, then move graph tensors to the model device."""
        metadata = dict(state.metadata)
        x, edge_attr = state.x, state.edge_attr
        if self.normalizer is not None:
            fingerprint = metadata.get("normalization_fingerprint")
            if fingerprint and fingerprint != self.normalizer.fingerprint:
                raise ValueError("Input was normalized with a different feature schema")
            if not fingerprint:
                x = self.normalizer.transform(x, "node")
                edge_attr = self.normalizer.transform(edge_attr, "edge")
                metadata["normalization_fingerprint"] = self.normalizer.fingerprint
        return replace(state, x=x.to(self.device), edge_index=state.edge_index.to(self.device),
                       edge_attr=edge_attr.to(self.device), metadata=metadata)

    @torch.no_grad()
    def forecast(self, states, steps: int) -> dict[str, Any]:
        self.ensure_loaded()
        prepared = [self._prepare_state(state) for state in states]
        return self.model.forecast(prepared, k=steps, explain=False)

    def explain(self, state, k: int = 4, topk: int = 10) -> list[dict[str, Any]]:
        """Gradient-based feature attribution via the existing ML primitive.

        Note: intentionally NOT under torch.no_grad() — attribution needs gradients.
        """
        self.ensure_loaded()
        from cybermind.explainability.attribution import gradient_feature_attribution

        return gradient_feature_attribution(self.model, self._prepare_state(state), k=k, topk=topk)
