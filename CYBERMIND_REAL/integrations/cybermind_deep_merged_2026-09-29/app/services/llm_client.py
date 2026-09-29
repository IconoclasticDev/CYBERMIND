from __future__ import annotations

"""Shared LLM client for CYBERMIND Attack Labs (Strix probes + patcher).

Priority: local Ollama-compatible endpoint (OLLAMA_BASE_URL, default
http://127.0.0.1:11434). Any model works — drop in a 3B later via OLLAMA_MODEL.
Every caller must degrade gracefully: if no LLM is reachable, callers fall back
to the deterministic engines. The system never blocks on the LLM.
"""

import os
from typing import Any

import httpx

from app.core.logging import log


class LLMClient:
    """Tiny async client over the Ollama /api/generate endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("OLLAMA_BASE_URL")
            or os.getenv("LLM_API_BASE")
            or "http://127.0.0.1:11434"
        ).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
        self.timeout = timeout
        self._available: bool | None = None

    # ------------------------------------------------------------- availability
    def status(self) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=1.2) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", [])]
                    self._available = True
                    return {
                        "available": True,
                        "provider": "ollama",
                        "url": self.base_url,
                        "model": self.model if self.model in models else (models[0] if models else self.model),
                        "models": models,
                    }
        except Exception:  # noqa: BLE001
            pass
        self._available = False
        return {
            "available": False,
            "provider": "none",
            "url": self.base_url,
            "model": self.model,
            "models": [],
        }

    # ---------------------------------------------------------------- generation
    async def generate(self, prompt: str, max_tokens: int = 400) -> str | None:
        """One-shot generation. Returns None on any failure (caller falls back)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": max_tokens},
                    },
                )
                if res.status_code == 200:
                    text = (res.json().get("response") or "").strip()
                    return text or None
        except Exception as exc:  # noqa: BLE001
            log.debug("LLM generate failed: %s", exc)
        return None


_shared: LLMClient | None = None


def get_llm() -> LLMClient:
    global _shared
    if _shared is None:
        _shared = LLMClient()
    return _shared
