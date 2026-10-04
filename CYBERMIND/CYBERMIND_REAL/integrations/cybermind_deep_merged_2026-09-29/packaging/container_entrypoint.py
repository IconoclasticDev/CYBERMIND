"""Run the bundled API and the isolated HTTP Attack Lab in one container."""
from __future__ import annotations

import json
import signal
import subprocess
import sys
import time
from urllib.request import urlopen


def main() -> int:
    children: list[subprocess.Popen] = []

    def stop_children(*_args) -> None:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()

    signal.signal(signal.SIGTERM, stop_children)
    signal.signal(signal.SIGINT, stop_children)
    try:
        sandbox = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "sandbox.target_app:app",
            "--host", "127.0.0.1", "--port", "8081",
        ])
        children.append(sandbox)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if sandbox.poll() is not None:
                raise RuntimeError("Loopback sandbox exited before becoming ready")
            try:
                with urlopen("http://127.0.0.1:8081/sandbox/health", timeout=1) as response:
                    json.load(response)
                break
            except (OSError, ValueError):
                time.sleep(0.2)
        else:
            raise RuntimeError("Loopback sandbox health check timed out")
        print("[CYBERMIND] Attack Lab sandbox ready at 127.0.0.1:8081", flush=True)
        api = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0", "--port", "8000",
        ])
        children.append(api)
        reported_expiry = False
        while api.poll() is None:
            if sandbox.poll() is not None and not reported_expiry:
                # Preserve the existing one-hour safety lifetime; never silently
                # restart the sandbox or claim it is still reachable.
                print("[CYBERMIND] Sandbox stopped; restart the app to start a new lab session", flush=True)
                reported_expiry = True
            time.sleep(0.3)
        return api.returncode or 0
    finally:
        stop_children()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
