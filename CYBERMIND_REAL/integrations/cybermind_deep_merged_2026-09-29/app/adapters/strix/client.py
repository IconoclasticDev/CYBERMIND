from __future__ import annotations

"""Thin, safe abstraction over Strix execution (local CLI or docker).

Builds the exact headless invocation documented by upstream Strix:
    strix -n --target <t> [--instruction <s>] [--scan-mode quick] [--max-budget N]
Artifacts land in <STRIX_RUNS_DIR>/<run_name>/. Credentials never appear in
argv or logs — they are passed through the child process environment only.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.core.logging import log


class StrixClient:
    """Command builder + availability probing for the Strix CLI."""

    def __init__(
        self,
        strix_bin: str = "strix",
        runs_dir: str | None = None,
        llm_model: str | None = None,
        llm_api_key_env: str = "LLM_API_KEY",
        llm_api_base: str | None = None,
        timeout: float = 1800.0,
        max_budget: float | None = None,
    ) -> None:
        self.strix_bin = strix_bin
        self.runs_dir = runs_dir
        self.llm_model = llm_model
        self.llm_api_key_env = llm_api_key_env
        self.llm_api_base = llm_api_base
        self.timeout = timeout
        self.max_budget = max_budget

    # ---------------------------------------------------------- availability
    def available(self) -> bool:
        """True when the strix binary can be located.

        Located = resolvable via PATH lookup (shutil.which), or an explicit
        path that exists. We deliberately do not execute `--version` here:
        probing must stay cheap, side-effect free and shell-free.
        """
        if not self.strix_bin:
            return False
        if shutil.which(self.strix_bin):
            return True
        p = Path(self.strix_bin)
        return p.is_file() and ("/" in self.strix_bin or "\\" in self.strix_bin)

    def availability(self) -> dict[str, Any]:
        ok = self.available()
        return {
            "available": ok,
            "binary": self.strix_bin,
            "reason": None if ok else "validation engine binary not found or not runnable (set VALIDATOR_BIN)",
        }

    # ------------------------------------------------------------ env passing
    def child_env(self, base_env: dict[str, str] | None = None) -> dict[str, str]:
        """Environment for the child process. Keys are passed through from the
        parent environment; values are never logged or stored."""
        import os

        env = dict(base_env or os.environ)
        if self.llm_model:
            env["STRIX_LLM"] = self.llm_model
        if self.llm_api_base:
            env["LLM_API_BASE"] = self.llm_api_base
        # LLM_API_KEY passes through untouched if present in the parent env.
        return env

    # ---------------------------------------------------------- command build
    def build_command(
        self,
        target: str,
        instruction: str | None = None,
        scan_mode: str = "quick",
        max_budget: float | None = None,
    ) -> list[str]:
        """Construct the headless strix invocation. Target is validated
        upstream by the SafetyGate; here we only assert basic sanity."""
        if not target or any(c in target for c in "\r\n\x00"):
            raise ValueError("invalid target string")
        if instruction and any(c in instruction for c in "\x00"):
            raise ValueError("invalid instruction string")
        cmd = [self.strix_bin, "-n", "--target", target]
        if instruction:
            cmd += ["--instruction", instruction]
        if scan_mode in ("quick", "standard", "deep"):
            cmd += ["--scan-mode", scan_mode]
        budget = max_budget if max_budget is not None else self.max_budget
        if budget is not None and budget > 0:
            cmd += ["--max-budget", str(float(budget))]
        return cmd

    @staticmethod
    def parse_exit_code(returncode: int) -> str:
        """Map documented Strix exit codes to run status."""
        return {0: "completed", 1: "failed", 2: "completed_findings"}.get(
            returncode if returncode in (0, 1, 2) else -1, "failed"
        )

    def log_safe(self, cmd: list[str]) -> str:
        """Redacted argv for logs (no secrets ever appear in argv anyway)."""
        return subprocess.list2cmdline(cmd)
