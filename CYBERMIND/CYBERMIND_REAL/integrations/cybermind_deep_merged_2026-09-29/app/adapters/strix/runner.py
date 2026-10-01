from __future__ import annotations

"""Async Strix run manager.

Runs execute as subprocesses via asyncio (never blocking FastAPI worker
threads). Each run gets a run_id, hard timeout, and on completion its
structured artifacts are collected and parsed.
"""

import asyncio
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from app.adapters.strix.artifacts import ArtifactCollector
from app.adapters.strix.client import StrixClient
from app.adapters.strix.parser import StrixArtifactParser
from app.adapters.strix.schemas import ExecutionMode, RunStatus, StrixRunConfig, StrixRunRecord
from app.adapters.strix.safety import SafetyGate
from app.core.logging import log


class StrixRunner:
    """Lifecycle management for authorized Strix validation runs."""

    def __init__(
        self,
        client: StrixClient,
        gate: SafetyGate,
        artifacts_dir: Path,
        default_timeout: float = 1800.0,
    ) -> None:
        self.client = client
        self.gate = gate
        self.collector = ArtifactCollector(artifacts_dir)
        self.parser = StrixArtifactParser()
        self.default_timeout = default_timeout
        self.runs: dict[str, StrixRunRecord] = {}
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._callbacks: list[Any] = []  # fn(event_type: str, payload: dict)

    # ------------------------------------------------------------- callbacks
    def on_event(self, fn: Any) -> None:
        self._callbacks.append(fn)

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        for fn in self._callbacks:
            try:
                fn(event, payload)
            except Exception as exc:  # noqa: BLE001
                log.warning("strix event callback failed: %s", exc)

    # ----------------------------------------------------------------- status
    def availability(self) -> dict[str, Any]:
        return self.client.availability()

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        runs = sorted(self.runs.values(), key=lambda r: r.started_at, reverse=True)[:limit]
        return [r.to_dict() for r in runs]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        rec = self.runs.get(run_id)
        return rec.to_dict() if rec else None

    # ------------------------------------------------------------------- runs
    async def start_run(self, config: StrixRunConfig, autonomous: bool = False) -> dict[str, Any]:
        """Authorize + launch a Strix run. Raises AuthorizationError when the
        target is unregistered or the environment is not permitted."""
        # HARD BOUNDARY: registration + environment checks happen here.
        if autonomous:
            self.gate.authorize_autonomous(config.target)
        else:
            self.gate.authorize(config.target)

        if not self.client.available():
            raise RuntimeError("VALIDATION_UNAVAILABLE: validation engine binary not found (set VALIDATOR_BIN)")

        run_id = uuid.uuid4().hex[:12]
        rec = StrixRunRecord(
            run_id=run_id,
            scenario_id=config.scenario_id,
            started_at=time.time(),
            status=RunStatus.RUNNING,
            target=config.target,
            mode=config.execution_mode.value if isinstance(config.execution_mode, ExecutionMode) else str(config.execution_mode),
            budget=config.max_budget,
        )
        self.runs[run_id] = rec
        self._emit("strix.run_started", rec.to_dict())
        task = asyncio.get_running_loop().create_task(self._execute(rec, config))
        self._tasks[run_id] = task
        return rec.to_dict()

    async def _execute(self, rec: StrixRunRecord, config: StrixRunConfig) -> None:
        cmd = self.client.build_command(
            target=config.target,
            instruction=config.instruction,
            scan_mode=config.scan_mode,
            max_budget=config.max_budget,
        )
        timeout = config.timeout or self.default_timeout
        started = rec.started_at
        # Child CWD = our managed runs dir so Strix artifacts (strix_runs/...)
        # land in a predictable place; the collector scans the same root.
        workdir = self.collector.runs_root
        workdir.mkdir(parents=True, exist_ok=True)
        try:
            log.info("strix run %s starting: %s", rec.run_id, self.client.log_safe(cmd))
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=self.client.child_env(),
                cwd=str(workdir),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._processes[rec.run_id] = proc
            try:
                out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                rec.return_code = proc.returncode
                rec.status = RunStatus(self.client.parse_exit_code(proc.returncode))
            except asyncio.TimeoutError:
                rec.status = RunStatus.TIMEOUT
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                log.warning("strix run %s timed out after %.0fs", rec.run_id, timeout)
        except FileNotFoundError:
            rec.status = RunStatus.FAILED
            rec.error = "strix binary not found"
        except Exception as exc:  # noqa: BLE001
            rec.status = RunStatus.FAILED
            rec.error = str(exc)[:300]
            log.exception("strix run %s failed", rec.run_id)
        finally:
            rec.finished_at = time.time()
            self._processes.pop(rec.run_id, None)
            # Collect artifacts when the run produced them.
            if rec.status not in (RunStatus.FAILED,) or rec.return_code in (0, 2):
                run_dir = self.collector.latest_run_dir(since=started)
                if run_dir is not None:
                    dest = self.collector.collect(run_dir, Path(self.collector.runs_root) / f"cybermind-{rec.run_id}")
                    rec.artifacts_path = str(dest)
            self._emit(
                "strix.run_completed",
                {**rec.to_dict(), "artifacts_path": rec.artifacts_path},
            )

    async def stop_run(self, run_id: str) -> dict[str, Any]:
        rec = self.runs.get(run_id)
        if rec is None:
            return {"error": "run not found", "run_id": run_id}
        proc = self._processes.get(run_id)
        if proc is not None and proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        task = self._tasks.get(run_id)
        if task is not None and not task.done():
            task.cancel()
        rec.status = RunStatus.STOPPED
        rec.finished_at = time.time()
        return rec.to_dict()

    async def collect_run(self, run_id: str) -> dict[str, Any]:
        """Parse collected artifacts into normalized findings + summary."""
        rec = self.runs.get(run_id)
        if rec is None:
            return {"error": "run not found", "run_id": run_id}
        if not rec.artifacts_path:
            return {**rec.to_dict(), "parsed": None, "note": "no artifacts collected (run failed or produced none)"}
        artifacts = self.collector.load_artifacts(rec.artifacts_path)
        parsed = self.parser.parse(artifacts)
        return {**rec.to_dict(), "parsed": parsed}

    def get_parsed(self, run_id: str) -> dict[str, Any] | None:
        """Synchronously load parsed results for a finished run (for the validation loop)."""
        rec = self.runs.get(run_id)
        if rec is None or not rec.artifacts_path:
            return None
        artifacts = self.collector.load_artifacts(rec.artifacts_path)
        return self.parser.parse(artifacts)

    def shutdown(self) -> None:
        for run_id in list(self._processes):
            proc = self._processes.get(run_id)
            if proc is not None and proc.returncode is None:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
