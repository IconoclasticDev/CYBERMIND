from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
DATA_ROOT = (
    Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "CYBERMIND" / "data"
    if getattr(sys, "frozen", False)
    else PROJECT_ROOT / "data"
)

@dataclass(frozen=True)
class Settings:
    # CYBERMIND_MODEL_PATH overrides the bundled checkpoint; defaults to the
    # project-local models/best.pt (the selected checkpoint bundled with this UI).
    model_path: Path = Path(os.getenv(
        "CYBERMIND_MODEL_PATH",
        str(PROJECT_ROOT / "models" / "best.pt"),
    ))
    export_path: Path = PROJECT_ROOT / "export" / "cybermind_compact.onnx"
    replay_dir: Path = DATA_ROOT / "replay"
    test_cases_dir: Path = PROJECT_ROOT / "data" / "test_cases"
    runs_dir: Path = DATA_ROOT / "runs"
    host: str = os.getenv("CYBERMIND_HOST", "127.0.0.1")
    port: int = int(os.getenv("CYBERMIND_PORT", "8000"))
    device: str = os.getenv("CYBERMIND_DEVICE", "auto")
    rollout_steps: int = int(os.getenv("CYBERMIND_ROLLOUT_STEPS", "12"))
    # --- Validation engine adapter (controlled adversarial validation layer) ---
    # VALIDATOR_* is the user-facing naming; legacy STRIX_* env vars still work.
    strix_bin: str = os.getenv("VALIDATOR_BIN", os.getenv("STRIX_BIN", "strix"))
    strix_llm: str | None = os.getenv("VALIDATOR_LLM", os.getenv("STRIX_LLM"))
    strix_runs_dir: Path = Path(os.getenv(
        "VALIDATOR_RUNS_DIR",
        os.getenv("STRIX_RUNS_DIR", str(DATA_ROOT / "strix_runs")),
    ))
    strix_timeout: float = float(os.getenv("VALIDATOR_TIMEOUT", os.getenv("STRIX_TIMEOUT", "1800")))
    strix_max_budget: float | None = (
        float(v) if (v := os.getenv("VALIDATOR_MAX_BUDGET", os.getenv("STRIX_MAX_BUDGET"))) else None
    )
    # LLM_API_KEY / LLM_API_BASE are read from the process env by the validation
    # client and passed only to the child process; never logged or persisted.

settings = Settings()
for _p in (settings.replay_dir, settings.test_cases_dir, settings.runs_dir, settings.strix_runs_dir):
    _p.mkdir(parents=True, exist_ok=True)

