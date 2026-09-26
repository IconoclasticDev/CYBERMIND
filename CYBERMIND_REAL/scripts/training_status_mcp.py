#!/usr/bin/env python3
"""MCP resource and tool backed by credit-free 15-minute local snapshots."""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
LATEST = RESULTS / "training_status_latest.json"
HISTORY = RESULTS / "training_status_15min.jsonl"
PIPELINE_STATE = ROOT / "data/manifests/economy_pipeline"
REAL_PIPELINE_STATE = ROOT / "data/manifests/real_best_pipeline"
TOTAL_DATASET_BYTES = 486_140_743_183
INTERVAL_SECONDS = int(os.environ.get("CYBERMIND_STATUS_INTERVAL", "900"))


def command(*args: str) -> str:
    try:
        return subprocess.run(args, check=False, capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception as error:
        return f"unavailable: {error}"


def directory_bytes(path: Path) -> int:
    total = 0
    if path.exists():
        for item in path.rglob("*"):
            try:
                if item.is_file():
                    total += item.stat().st_size
            except OSError:
                pass
    return total


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def snapshot() -> dict:
    markers = sorted(path.stem for path in PIPELINE_STATE.glob("*.complete"))
    real_markers = sorted(path.stem for path in REAL_PIPELINE_STATE.glob("*.complete"))
    improved_service = command("supervisorctl", "status", "cybermind_improved")
    improved_status = load_json(RESULTS / "stage_expansion_improved/status.json")
    improved_active = ("RUNNING" in improved_service or "STARTING" in improved_service or
                       improved_status is not None)
    real_service = command("supervisorctl", "status", "cybermind_real_best")
    real_active = bool(real_markers) or "RUNNING" in real_service or "STARTING" in real_service
    if improved_active:
        training_status = improved_status
        history = load_json(RESULTS / "stage_expansion_improved/train_history.json") or []
        checkpoint = ROOT / "checkpoints/stage_expansion_improved/best.pt"
    elif real_active:
        training_status = load_json(RESULTS / "real_best/status.json")
        history = load_json(RESULTS / "real_best/train_history.json") or []
        checkpoint = ROOT / "checkpoints/real_best/best.pt"
    else:
        training_status = load_json(RESULTS / "gb10_economy_train_history_status.json")
        history = load_json(RESULTS / "gb10_economy_train_history.json") or []
        checkpoint = ROOT / "checkpoints/best_gb10_economy.pt"
    raw_bytes = directory_bytes(ROOT / "data/raw/CIC-IDS-2018")
    extended_service = command("supervisorctl", "status", "cybermind_extended")
    if improved_active and training_status and training_status.get("status") == "running":
        stage = "improved_future_state_training"
    elif improved_active:
        stage = "improved_future_state_training_complete"
    elif real_active and training_status and training_status.get("status") == "running":
        stage = "real_data_training"
    elif real_active and "evaluation" in real_markers:
        stage = "real_data_complete"
    elif real_active and "training" in real_markers:
        stage = "real_data_evaluation"
    elif real_active and "preparation" in real_markers:
        stage = "real_data_training_starting"
    elif real_active and "canonical" in real_markers:
        stage = "real_data_graph_preparation"
    elif real_active and "rebuild" in real_markers:
        stage = "real_data_validation"
    elif real_active:
        stage = "real_pcap_rebuild"
    elif training_status and training_status.get("status") == "running":
        stage = "training"
    elif "extended_training" in markers:
        stage = "extended_training_complete"
    elif "training" in markers:
        stage = "training_complete"
    elif "preparation" in markers:
        stage = "training_starting"
    elif "validation" in markers:
        stage = "preparing_graph_sequences"
    elif "download" in markers:
        stage = "validating_or_normalizing"
    else:
        stage = "downloading"
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "pipeline_service": command("supervisorctl", "status", "cybermind_economy"),
        "improved_training_service": improved_service,
        "extended_training_service": extended_service,
        "real_data_service": real_service,
        "downloaded_bytes": raw_bytes,
        "dataset_total_bytes": TOTAL_DATASET_BYTES,
        "download_percent": round(raw_bytes * 100 / TOTAL_DATASET_BYTES, 4),
        "completed_markers": markers,
        "real_data_completed_markers": real_markers,
        "training_status": training_status,
        "epochs_completed": len(history),
        "latest_epoch": history[-1] if history else None,
        "checkpoint_exists": checkpoint.is_file(),
        "checkpoint_bytes": checkpoint.stat().st_size if checkpoint.is_file() else 0,
        "gpu": command(
            "nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,power.draw",
            "--format=csv,noheader,nounits",
        ),
        "disk": command("df", "-h", "/workspace").splitlines()[-1],
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    temporary = LATEST.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, indent=2), encoding="utf-8")
    temporary.replace(LATEST)
    with HISTORY.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, separators=(",", ":")) + "\n")
    return record


def updater() -> None:
    while True:
        snapshot()
        time.sleep(INTERVAL_SECONDS)


mcp = FastMCP("CYBERMIND Training Status", host="127.0.0.1", port=17071)


@mcp.tool()
def get_training_status() -> dict:
    """Return the most recent automatic CYBERMIND training snapshot."""
    return load_json(LATEST) or snapshot()


@mcp.resource("status://cybermind/training")
def training_status_resource() -> str:
    """Current CYBERMIND pipeline and training status as JSON."""
    return json.dumps(load_json(LATEST) or snapshot(), indent=2)


if __name__ == "__main__":
    threading.Thread(target=updater, daemon=True).start()
    mcp.run(transport="streamable-http")
