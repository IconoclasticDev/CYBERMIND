"""Windows Explorer launcher for the prebuilt, fully local CYBERMIND Docker app."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

APP_URL = "http://127.0.0.1:8000/"
HEALTH_URL = APP_URL + "api/health"
IMAGE_NAMES = (
    ("cybermind/offline-app:2026-09-29", "cybermind-offline-app.tar"),
    ("cybermind/offline-decrypter:2026-09-29", "cybermind-offline-decrypter.tar"),
)


def bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def log(message: str) -> None:
    root = Path(os.environ.get("LOCALAPPDATA", str(bundle_root()))) / "CYBERMIND"
    root.mkdir(parents=True, exist_ok=True)
    with (root / "launcher.log").open("a", encoding="utf-8") as handle:
        handle.write(time.strftime("%Y-%m-%d %H:%M:%S") + " " + message + "\n")


def show_error(message: str) -> None:
    log("ERROR " + message)
    ctypes.windll.user32.MessageBoxW(None, message, "CYBERMIND offline launcher", 0x10)


def docker_path() -> str:
    candidates = [
        shutil.which("docker"),
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DockerDesktop" / "resources" / "bin" / "docker.exe"),
        r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise RuntimeError("Docker CLI is not installed. Install Docker Desktop with the WSL 2 backend before opening this bundle.")


def run(command: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command[:4])}\n{(result.stderr or result.stdout)[-900:]}")
    return result


def ensure_docker(docker: str) -> None:
    try:
        run([docker, "info", "--format", "{{.ServerVersion}}"], timeout=12)
        return
    except (RuntimeError, subprocess.TimeoutExpired):
        pass
    desktop_candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DockerDesktop" / "Docker Desktop.exe",
        Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe"),
    ]
    desktop = next((path for path in desktop_candidates if path.is_file()), None)
    if desktop is None:
        raise RuntimeError("Docker Engine is stopped and Docker Desktop was not found. Start or install Docker Desktop, then reopen CYBERMIND.exe.")
    log("Starting Docker Desktop")
    subprocess.Popen([str(desktop)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            run([docker, "info", "--format", "{{.ServerVersion}}"], timeout=10)
            return
        except (RuntimeError, subprocess.TimeoutExpired):
            time.sleep(3)
    raise RuntimeError("Docker Desktop did not become ready within two minutes. Check that WSL 2 is installed and Docker Desktop can start, then reopen CYBERMIND.exe.")


def verify_tar(path: Path, expected: dict[str, object]) -> None:
    if not path.is_file() or path.stat().st_size != expected["bytes"]:
        raise RuntimeError(f"Offline image archive is missing or has the wrong size: {path.name}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected["sha256"]:
        raise RuntimeError(f"Offline image archive failed SHA-256 verification: {path.name}")


def ensure_images(docker: str, root: Path) -> None:
    manifest_path = root / "images" / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("Offline Docker image manifest is missing. Use the complete CYBERMIND bundle, not the EXE alone.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for image, filename in IMAGE_NAMES:
        try:
            run([docker, "image", "inspect", image], timeout=15)
            log(f"Image already loaded: {image}")
            continue
        except RuntimeError:
            pass
        path = root / "images" / filename
        expected = manifest.get(filename)
        if not isinstance(expected, dict):
            raise RuntimeError(f"No pinned hash for {filename}")
        log(f"Verifying and loading {filename}")
        verify_tar(path, expected)
        run([docker, "load", "--input", str(path)], timeout=1800)
        run([docker, "image", "inspect", image], timeout=15)


def wait_for_app(timeout_seconds: int = 120) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(HEALTH_URL, timeout=3) as response:
                health = json.load(response)
            if health.get("status") == "ok" and health.get("model", {}).get("available") is True:
                return
        except (OSError, URLError, ValueError):
            pass
        time.sleep(2)
    raise RuntimeError("The CYBERMIND container started but its model did not become ready. Inspect Docker Desktop and the launcher log.")


def main() -> int:
    try:
        root = bundle_root()
        compose = root / "compose.offline.yaml"
        if not compose.is_file():
            raise RuntimeError("compose.offline.yaml is missing beside CYBERMIND.exe.")
        docker = docker_path()
        ensure_docker(docker)
        ensure_images(docker, root)
        run([docker, "compose", "-p", "cybermind-offline", "-f", str(compose),
             "up", "-d", "--no-build", "--pull", "never"], timeout=180)
        wait_for_app()
        log("App ready at " + APP_URL)
        if os.environ.get("CYBERMIND_LAUNCHER_NO_BROWSER") != "1":
            webbrowser.open(APP_URL)
        return 0
    except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        show_error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
