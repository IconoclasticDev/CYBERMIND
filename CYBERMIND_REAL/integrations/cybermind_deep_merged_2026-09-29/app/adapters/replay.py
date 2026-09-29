from __future__ import annotations
from pathlib import Path
from typing import Any
from .scenario_base import ScenarioAdapter
from app.services.replay_service import ReplayService

class ReplayScenarioAdapter(ScenarioAdapter):
    def __init__(self, replay_root: Path) -> None:
        self.replay_root = replay_root.resolve()
        self.replay = ReplayService()
        self.active: dict[str, bool] = {}

    def _file(self, scenario_id: str) -> Path:
        candidate = (self.replay_root / f"{scenario_id}.jsonl").resolve()
        if self.replay_root not in candidate.parents:
            raise ValueError("invalid scenario path")
        return candidate

    def start(self, scenario_id: str) -> dict[str, Any]:
        if not self._file(scenario_id).exists():
            return {"scenario_id": scenario_id, "status": "not_found"}
        self.active[scenario_id] = True
        return {"scenario_id": scenario_id, "status": "ready", "mode": "replay"}

    def stop(self, scenario_id: str) -> dict[str, Any]:
        self.active[scenario_id] = False
        return {"scenario_id": scenario_id, "status": "stopped"}

    def reset(self, scenario_id: str) -> dict[str, Any]:
        self.active[scenario_id] = False
        return {"scenario_id": scenario_id, "status": "reset"}

    def status(self, scenario_id: str) -> dict[str, Any]:
        return {"scenario_id": scenario_id, "active": self.active.get(scenario_id, False)}

    def collect(self, scenario_id: str) -> list[dict[str, Any]]:
        return list(self.replay.stream(self._file(scenario_id)))
