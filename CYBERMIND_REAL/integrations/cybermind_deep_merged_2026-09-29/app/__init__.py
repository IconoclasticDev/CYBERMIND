"""CYBERMIND app package.

Ensures the ML research core (src/cybermind) is importable before any app
module loads, regardless of entrypoint (uvicorn, tests, scripts).
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
