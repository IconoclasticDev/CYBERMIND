from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Iterator

class ReplayService:
    """Read-only local JSONL replay helper. No network access."""
    def stream(self, path: Path) -> Iterator[dict[str, Any]]:
        path = path.resolve()
        if not path.exists() or path.parent not in {path.parent}:
            raise FileNotFoundError(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                yield json.loads(line)
