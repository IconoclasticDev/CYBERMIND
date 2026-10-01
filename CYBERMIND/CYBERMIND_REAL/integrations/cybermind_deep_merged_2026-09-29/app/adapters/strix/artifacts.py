from __future__ import annotations

"""Collect and package Strix run artifacts.

Strix writes its own structured artifacts to `<STRIX_RUNS_DIR>/<run_name>/`:
vulnerabilities.json, scan_metadata.json, agent_traces.json,
tool_executions.json, penetration_test_report.md. We never scrape terminal
text when artifacts exist.
"""

import shutil
from pathlib import Path
from typing import Any

from app.core.logging import log

ARTIFACT_FILES = (
    "vulnerabilities.json",
    "scan_metadata.json",
    "agent_traces.json",
    "tool_executions.json",
    "penetration_test_report.md",
)


class ArtifactCollector:
    """Locates Strix run artifacts and copies them into the CYBERMIND data dir."""

    def __init__(self, runs_root: Path) -> None:
        self.runs_root = Path(runs_root)
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def latest_run_dir(self, since: float = 0.0) -> Path | None:
        """Newest artifact directory modified after `since` (epoch seconds).

        Searches runs_root and one level of nested candidates (Strix may write
        to <cwd>/strix_runs/<name> while runs_root is <cwd>, or vice versa).
        """
        candidates: list[tuple[float, Path]] = []
        roots = [self.runs_root]
        nested = self.runs_root / "strix_runs"
        if nested.is_dir():
            roots.append(nested)
        elif self.runs_root.parent.name == "strix_runs":
            roots.append(self.runs_root.parent)
        for root in roots:
            if not root.exists():
                continue
            for p in root.iterdir():
                if not p.is_dir():
                    continue
                try:
                    # A run dir's freshness = max(its mtime, newest artifact
                    # file inside). Overwriting artifacts in place updates
                    # file mtimes but not necessarily the directory's.
                    mtimes = [p.stat().st_mtime]
                    for f in p.iterdir():
                        if f.is_file():
                            mtimes.append(f.stat().st_mtime)
                    mtime = max(mtimes)
                except OSError:
                    continue
                if mtime >= since - 5:
                    candidates.append((mtime, p))
        return max(candidates)[1] if candidates else None

    def collect(self, run_dir: Path | str, dest: Path | str) -> Path:
        """Copy known artifact files from run_dir into dest. Returns dest."""
        src, dst = Path(run_dir), Path(dest)
        dst.mkdir(parents=True, exist_ok=True)
        copied: list[str] = []
        for name in ARTIFACT_FILES:
            f = src / name
            if f.exists():
                shutil.copy2(f, dst / name)
                copied.append(name)
        if not copied:
            log.warning("no strix artifacts found in %s", src)
        return dst

    def load_artifacts(self, artifacts_path: Path | str) -> dict[str, Any]:
        """Read the collected artifacts back as structured data."""
        import json

        base = Path(artifacts_path)
        out: dict[str, Any] = {"path": str(base), "files": []}
        vulns = base / "vulnerabilities.json"
        if vulns.exists():
            try:
                out["vulnerabilities"] = json.loads(vulns.read_text(encoding="utf-8"))
                out["files"].append("vulnerabilities.json")
            except Exception as exc:  # noqa: BLE001
                log.warning("failed to parse %s: %s", vulns, exc)
                out["vulnerabilities"] = []
        meta = base / "scan_metadata.json"
        if meta.exists():
            try:
                out["scan_metadata"] = json.loads(meta.read_text(encoding="utf-8"))
                out["files"].append("scan_metadata.json")
            except Exception as exc:  # noqa: BLE001
                log.warning("failed to parse %s: %s", meta, exc)
        report = base / "penetration_test_report.md"
        if report.exists():
            out["report_md"] = report.read_text(encoding="utf-8", errors="replace")[:20000]
            out["files"].append("penetration_test_report.md")
        return out
