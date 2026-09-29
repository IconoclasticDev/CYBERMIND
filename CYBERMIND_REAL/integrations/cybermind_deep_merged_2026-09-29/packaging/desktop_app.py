"""Native Windows desktop window for the bundled CYBERMIND backend and React UI.

The backend uses a private ephemeral loopback socket as in-process UI transport.
No browser, Docker daemon, or fixed public port is started by this executable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import traceback
from urllib.request import Request, urlopen


def run_sandbox_child() -> None:
    """Run only the bundled loopback demonstration target in a separate process."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import uvicorn
    from sandbox.target_app import app as sandbox_app

    uvicorn.run(sandbox_app, host="127.0.0.1", port=8081, log_level="warning", access_log=False)


if __name__ == "__main__" and "--cybermind-sandbox-target" in sys.argv:
    run_sandbox_child()
    raise SystemExit(0)

def _startup_marker(stage: str) -> None:
    root = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "CYBERMIND"
    root.mkdir(parents=True, exist_ok=True)
    with (root / "desktop.log").open("a", encoding="utf-8") as stream:
        stream.write(time.strftime("%Y-%m-%d %H:%M:%S") + " import: " + stage + "\n")


_startup_marker("stdlib ready")
from PySide6.QtCore import QStandardPaths, QTimer, QUrl
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEnginePage, QWebEnginePermission, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
_startup_marker("Qt ready")
import uvicorn
_startup_marker("Uvicorn ready")
from app.main import app as api_app
_startup_marker("backend modules ready")


def app_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def user_root() -> Path:
    root = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "CYBERMIND"
    root.mkdir(parents=True, exist_ok=True)
    return root


def log(message: str) -> None:
    with (user_root() / "desktop.log").open("a", encoding="utf-8") as stream:
        stream.write(time.strftime("%Y-%m-%d %H:%M:%S") + " " + message + "\n")


def start_backend() -> tuple[uvicorn.Server, threading.Thread, int]:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    config = uvicorn.Config(api_app, host="127.0.0.1", port=port,
                            log_level="warning", access_log=False, log_config=None)
    server = uvicorn.Server(config)

    def serve() -> None:
        try:
            server.run(sockets=[listener])
        except Exception as exc:  # pragma: no cover - visible through startup timeout/log
            log("Backend failed:\n" + traceback.format_exc())
        finally:
            listener.close()

    thread = threading.Thread(target=serve, name="cybermind-backend", daemon=True)
    thread.start()
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if not thread.is_alive():
            raise RuntimeError("CYBERMIND backend exited during startup. See desktop.log.")
        try:
            with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
                status = json.load(response)
            if status.get("status") == "ok" and status.get("model", {}).get("available"):
                log(f"Model ready: {status['model']['version']}")
                return server, thread, port
        except (OSError, ValueError):
            pass
        time.sleep(0.25)
    server.should_exit = True
    raise RuntimeError("CYBERMIND model did not become ready within 90 seconds. See desktop.log.")


def start_sandbox(backend_port: int) -> subprocess.Popen | None:
    """Start the bundled probe target only if no CYBERMIND target is already live."""
    url = "http://127.0.0.1:8081/sandbox/health"
    try:
        with urlopen(url, timeout=1) as response:
            if json.load(response).get("status") == "LIVE_ISOLATED_SANDBOX":
                log("Existing loopback sandbox target is ready")
                return None
    except (OSError, ValueError):
        pass
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    environment = os.environ.copy()
    environment["CYBERMIND_BACKEND_URL"] = f"http://127.0.0.1:{backend_port}"
    child = subprocess.Popen(
        [sys.executable, "--cybermind-sandbox-target"],
        cwd=str(app_root()), env=environment, creationflags=flags,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and child.poll() is None:
        try:
            with urlopen(url, timeout=1) as response:
                if json.load(response).get("status") == "LIVE_ISOLATED_SANDBOX":
                    log(f"Bundled loopback sandbox ready; pid={child.pid}")
                    return child
        except (OSError, ValueError):
            time.sleep(0.25)
    log(f"Bundled sandbox failed to start; exit={child.poll()}")
    if child.poll() is None:
        child.terminate()
    return None


def main() -> int:
    root = app_root()
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ["CYBERMIND_DEVICE"] = "cpu"
    # A frozen GUI process does not always inherit Docker Desktop's PATH.
    # Expose its CLI to the validator when Docker is installed on this host.
    docker_bins = (
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DockerDesktop" / "resources" / "bin",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Docker" / "Docker" / "resources" / "bin",
    )
    for docker_bin in docker_bins:
        if (docker_bin / "docker.exe").is_file():
            os.environ["PATH"] = str(docker_bin) + os.pathsep + os.environ.get("PATH", "")
            break
    qt = QApplication(sys.argv)
    qt.setApplicationName("CYBERMIND")
    try:
        server, thread, port = start_backend()
    except Exception as exc:
        log("Startup error:\n" + traceback.format_exc())
        QMessageBox.critical(None, "CYBERMIND could not start", str(exc))
        return 1

    sandbox_process = start_sandbox(port)

    storage = user_root() / "webview"
    storage.mkdir(parents=True, exist_ok=True)
    profile = QWebEngineProfile.defaultProfile()
    profile.setPersistentStoragePath(str(storage))
    profile.setCachePath(str(storage / "cache"))

    window = QWebEngineView()
    window.setWindowTitle("CYBERMIND — Analyst Console")
    window.resize(1440, 900)
    window.setMinimumSize(960, 640)

    def grant_local_clipboard(permission: QWebEnginePermission) -> None:
        origin = permission.origin()
        if (
            permission.permissionType() == QWebEnginePermission.PermissionType.ClipboardReadWrite
            and origin.scheme() == "http"
            and origin.host() == "127.0.0.1"
            and origin.port() == port
        ):
            permission.grant()

    window.page().permissionRequested.connect(grant_local_clipboard)
    window.page().setFeaturePermission(
        QUrl(f"http://127.0.0.1:{port}"),
        QWebEnginePage.Feature.ClipboardReadWrite,
        QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
    )
    active_downloads: dict[int, QWebEngineDownloadRequest] = {}

    def notify_download(filename: str, status: str, error: str = "") -> None:
        detail = json.dumps({"filename": filename, "status": status, "error": error})
        window.page().runJavaScript(
            "window.dispatchEvent(new CustomEvent('cybermind:download', "
            f"{{detail: {detail}}}));"
        )

    def handle_download(request: QWebEngineDownloadRequest) -> None:
        filename = Path(request.suggestedFileName() or request.downloadFileName() or "report.json").name
        downloads = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        initial = str(Path(downloads or str(Path.home())) / filename)
        selected, _ = QFileDialog.getSaveFileName(
            window, "Save report", initial, "JSON files (*.json);;All files (*)"
        )
        if not selected:
            request.cancel()
            notify_download(filename, "cancelled", "Save was cancelled; no report was downloaded.")
            return

        destination = Path(selected)
        request.setDownloadDirectory(str(destination.parent))
        request.setDownloadFileName(destination.name)
        active_downloads[request.id()] = request

        def on_state_changed(state: QWebEngineDownloadRequest.DownloadState) -> None:
            if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                if destination.is_file() and destination.stat().st_size > 0:
                    notify_download(filename, "completed")
                else:
                    notify_download(filename, "failed", "Download completed without a saved report file.")
            elif state in (
                QWebEngineDownloadRequest.DownloadState.DownloadCancelled,
                QWebEngineDownloadRequest.DownloadState.DownloadInterrupted,
            ):
                notify_download(filename, "failed", request.interruptReasonString() or "Report download failed.")
            else:
                return
            active_downloads.pop(request.id(), None)

        request.stateChanged.connect(on_state_changed)
        request.accept()

    profile.downloadRequested.connect(handle_download)
    window.loadFinished.connect(
        lambda ok: window.page().runJavaScript("window.__CYBERMIND_DESKTOP__ = true;") if ok else None
    )
    window.load(QUrl(f"http://127.0.0.1:{port}/"))
    window.show()

    smoke_path = os.getenv("CYBERMIND_DESKTOP_SMOKE_SCREENSHOT")
    if smoke_path:
        def finish_smoke() -> None:
            window.grab().save(smoke_path)
            log(f"Smoke screenshot: {smoke_path}")
            qt.quit()
        QTimer.singleShot(8000, finish_smoke)

    def shutdown() -> None:
        if sandbox_process is not None and sandbox_process.poll() is None:
            try:
                urlopen(Request("http://127.0.0.1:8081/sandbox/destroy", method="POST"), timeout=2).close()
                sandbox_process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                sandbox_process.terminate()
        server.should_exit = True
        thread.join(timeout=5)
        log("Desktop stopped")

    qt.aboutToQuit.connect(shutdown)
    log(f"Desktop window opened; private UI transport on 127.0.0.1:{port}")
    return qt.exec()


if __name__ == "__main__":
    raise SystemExit(main())
