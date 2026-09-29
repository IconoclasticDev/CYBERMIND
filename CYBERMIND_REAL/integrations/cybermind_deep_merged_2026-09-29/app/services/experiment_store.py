from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any


class ExperimentStore:
    """Durable local run records (JSON files under data/runs)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def create_run(
        self,
        scenario_id: str | None = None,
        model_version: str | None = None,
        source: str = "api",
        config_hash: str | None = None,
    ) -> dict[str, Any]:
        run_id = uuid.uuid4().hex[:12]
        record = {
            "run_id": run_id,
            "scenario_id": scenario_id,
            "model_version": model_version,
            "source": source,
            "config_hash": config_hash,
            "start_time": time.time(),
            "end_time": None,
            "predictions": [],
            "interventions": [],
            "metrics": {},
            "provenance": {"created_by": "cybermind-app"},
        }
        self.save(record)
        return record

    def save(self, record: dict[str, Any]) -> None:
        path = self.root / f"{record['run_id']}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)

    def get(self, run_id: str) -> dict[str, Any] | None:
        # Validate run_id to avoid path traversal.
        if not run_id or any(c not in "abcdef0123456789" for c in run_id):
            return None
        path = self.root / f"{run_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            runs.append({
                "run_id": rec.get("run_id"),
                "scenario_id": rec.get("scenario_id"),
                "model_version": rec.get("model_version"),
                "start_time": rec.get("start_time"),
                "end_time": rec.get("end_time"),
                "prediction_count": len(rec.get("predictions", [])),
                "intervention_count": len(rec.get("interventions", [])),
                "metrics": rec.get("metrics") or {},
            })
        return runs

    def append_prediction(self, run_id: str, prediction: dict[str, Any]) -> None:
        rec = self.get(run_id)
        if rec is None:
            return
        rec["predictions"].append(prediction)
        self.save(rec)

    def append_intervention(self, run_id: str, intervention: dict[str, Any]) -> None:
        rec = self.get(run_id)
        if rec is None:
            return
        rec["interventions"].append(intervention)
        self.save(rec)

    def close_run(self, run_id: str, metrics: dict[str, Any] | None = None) -> None:
        rec = self.get(run_id)
        if rec is None:
            return
        rec["end_time"] = time.time()
        if metrics:
            rec["metrics"].update(metrics)
        self.save(rec)
