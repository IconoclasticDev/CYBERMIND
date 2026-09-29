from __future__ import annotations
from typing import Any
from .scenario_base import ScenarioAdapter

class DockerSandboxAdapter(ScenarioAdapter):
    """Placeholder for the isolated sandbox integration.

    Do not expose arbitrary shell execution. The production adapter should call
    a fixed allow-listed scenario controller and consume telemetry from the
    isolated network only.
    """
    def _not_ready(self) -> dict[str, Any]:
        return {"status": "not_configured", "safe": True}
    def start(self, scenario_id: str) -> dict[str, Any]: return self._not_ready()
    def stop(self, scenario_id: str) -> dict[str, Any]: return self._not_ready()
    def reset(self, scenario_id: str) -> dict[str, Any]: return self._not_ready()
    def status(self, scenario_id: str) -> dict[str, Any]: return self._not_ready()
    def collect(self, scenario_id: str) -> list[dict[str, Any]]: return []
