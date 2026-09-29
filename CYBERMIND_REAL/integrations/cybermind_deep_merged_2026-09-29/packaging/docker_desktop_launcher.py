"""Windows desktop window backed by the bundled offline Docker image.

Docker serves the UI/API on loopback as an internal transport. The user sees a
native CYBERMIND window, not a browser tab. No registry pull is performed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time
import traceback
from urllib.request import urlopen

from PySide6.QtCore import QObject, QStandardPaths, QUrl, Signal
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEnginePage, QWebEnginePermission, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView

from windows_launcher import bundle_root, docker_path, ensure_docker, log, run, verify_tar

APP_IMAGE = "cybermind/offline-app:2026-09-29"
APP_ARCHIVE = "cybermind-offline-app.tar"


class StartSignals(QObject):
    ready = Signal(str)
    failed = Signal(str)


def start_container() -> str:
    root = bundle_root()
    compose = root / "compose.offline.yaml"
    if not compose.is_file():
        raise RuntimeError("compose.offline.yaml is missing beside CYBERMIND.exe.")
    docker = docker_path()
    ensure_docker(docker)
    manifest_path = root / "images" / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("Offline image manifest is missing. Keep the complete bundle together.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest.get(APP_ARCHIVE)
    if not isinstance(expected, dict):
        raise RuntimeError("Offline app image hash is missing from the manifest.")
    pinned_image_id = expected.get("image_id")
    try:
        loaded_image_id = run([docker, "image", "inspect", "--format", "{{.Id}}", APP_IMAGE], timeout=15).stdout.strip()
    except RuntimeError:
        loaded_image_id = None
    if pinned_image_id and loaded_image_id == pinned_image_id:
        log("Pinned bundled app image already loaded")
    else:
        archive = root / "images" / APP_ARCHIVE
        log("Verifying offline image archive")
        verify_tar(archive, expected)
        log("Loading offline app image")
        run([docker, "load", "--input", str(archive)], timeout=1800)
        loaded_image_id = run([docker, "image", "inspect", "--format", "{{.Id}}", APP_IMAGE], timeout=15).stdout.strip()
        if pinned_image_id and loaded_image_id != pinned_image_id:
            raise RuntimeError("Loaded app image does not match the pinned bundle image ID.")
    compose_cmd = [docker, "compose", "-p", "cybermind-offline", "-f", str(compose)]
    container_id = run([*compose_cmd, "ps", "-q", "cybermind"], timeout=15).stdout.strip()
    running_image_id = None
    if container_id:
        running_image_id = run([docker, "inspect", "--format", "{{.Image}}", container_id], timeout=15).stdout.strip()
    up_cmd = [*compose_cmd, "up", "-d", "--no-build", "--pull", "never"]
    if running_image_id and running_image_id != loaded_image_id:
        log("Replacing stale app container with the pinned bundled image")
        up_cmd.append("--force-recreate")
    run(up_cmd, timeout=180)
    published = run([docker, "compose", "-p", "cybermind-offline", "-f", str(compose),
                     "port", "cybermind", "8000"], timeout=15).stdout.strip()
    if not published.startswith("127.0.0.1:"):
        raise RuntimeError(f"Unexpected Docker port mapping: {published}")
    url = f"http://{published}/"
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            with urlopen(url + "api/health", timeout=3) as response:
                health = json.load(response)
            if health.get("status") == "ok" and health.get("model", {}).get("available") is True:
                log("Docker app ready for desktop window at " + url)
                return url
        except (OSError, ValueError):
            pass
        time.sleep(2)
    raise RuntimeError("The container started but its model did not become ready. Inspect Docker Desktop and launcher.log.")


def main() -> int:
    qt = QApplication([])
    qt.setApplicationName("CYBERMIND")
    storage = Path(os.environ.get("LOCALAPPDATA", str(bundle_root()))) / "CYBERMIND" / "docker-webview"
    storage.mkdir(parents=True, exist_ok=True)
    profile = QWebEngineProfile.defaultProfile()
    profile.setPersistentStoragePath(str(storage))
    profile.setCachePath(str(storage / "cache"))

    window = QWebEngineView()
    window.setWindowTitle("CYBERMIND — Analyst Console")
    window.resize(1440, 900)
    window.setMinimumSize(960, 640)
    window.setHtml("""<!doctype html><html><body style="margin:0;background:#f7f5f0;
      color:#1c232b;font:16px system-ui;display:grid;place-items:center;height:100vh">
      <div style="text-align:center"><h1 style="letter-spacing:.18em">CYBERMIND</h1>
      <p>Starting the offline application…</p></div></body></html>""")

    app_url = [""]

    def grant_local_clipboard(permission: QWebEnginePermission) -> None:
        origin = permission.origin()
        if (permission.permissionType() == QWebEnginePermission.PermissionType.ClipboardReadWrite
                and origin.scheme() == "http" and origin.host() == "127.0.0.1"
                and app_url[0] and origin.port() == QUrl(app_url[0]).port()):
            permission.grant()

    window.page().permissionRequested.connect(grant_local_clipboard)
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
        selected, _ = QFileDialog.getSaveFileName(window, "Save report", initial, "JSON files (*.json);;All files (*)")
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
            elif state in (QWebEngineDownloadRequest.DownloadState.DownloadCancelled,
                           QWebEngineDownloadRequest.DownloadState.DownloadInterrupted):
                notify_download(filename, "failed", request.interruptReasonString() or "Report download failed.")
            else:
                return
            active_downloads.pop(request.id(), None)

        request.stateChanged.connect(on_state_changed)
        request.accept()

    profile.downloadRequested.connect(handle_download)
    window.loadFinished.connect(
        lambda ok: window.page().runJavaScript("window.__CYBERMIND_DESKTOP__ = true;")
        if ok and window.url().host() == "127.0.0.1" else None
    )
    signals = StartSignals()

    def on_ready(url: str) -> None:
        app_url[0] = url
        window.page().setFeaturePermission(
            QUrl(url), QWebEnginePage.Feature.ClipboardReadWrite,
            QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
        )
        window.load(QUrl(url))

    signals.ready.connect(on_ready)

    def on_failed(message: str) -> None:
        QMessageBox.critical(window, "CYBERMIND could not start", message)
        qt.quit()

    signals.failed.connect(on_failed)

    def boot() -> None:
        try:
            signals.ready.emit(start_container())
        except Exception as exc:
            log("Startup error:\n" + traceback.format_exc())
            signals.failed.emit(str(exc))

    threading.Thread(target=boot, name="cybermind-docker-start", daemon=True).start()
    window.show()
    return qt.exec()


if __name__ == "__main__":
    raise SystemExit(main())
