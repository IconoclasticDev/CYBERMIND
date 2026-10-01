# CYBERMIND Docker desktop bundle

Keep this extracted folder intact. The image archive contains the React UI, FastAPI backend, pinned `best.pt` model, in-app report decrypter, and runtime dependencies. The image is loaded from the bundle; the launchers do not pull it from the internet.

## Windows

Install Docker Desktop with its Linux/WSL 2 engine once, then double-click **CYBERMIND.exe**. The EXE verifies and loads the image on first launch, starts the Docker service, and displays the app inside its own desktop window. It does not open a browser tab. The loopback address is an internal connection between the desktop window and Docker, not a remote service. The first launch may take several minutes while Docker loads the image. A later launch reuses the image and data volume.

The EXE is the Windows desktop launcher; the application backend and model run in Docker. The image archive and Compose file must remain beside the EXE. To stop the container without deleting saved cases, run `stop_windows.cmd`.

## Linux x86-64

Install Docker Engine and the Compose plugin, then run `sh launch_linux.sh` from this extracted folder. The script checks the image SHA-256, loads it without network access, starts the service, and opens an application-style window if Chromium or Chrome is installed. Otherwise it opens the default browser. Linux ARM64 and macOS images are not included. Run `sh stop_linux.sh` to stop the service without deleting saved cases.

## Included files

- `CYBERMIND.exe`: Windows Docker-backed desktop window.
- `launch_linux.sh`: Linux x86-64 Docker launcher.
- `compose.offline.yaml`: local Docker service and persistent volume.
- `images/cybermind-offline-app.tar`: complete offline app image, including `best.pt`.
- `images/manifest.json` and `images/SHA256SUMS`: pinned image integrity data.
- `demo/`: manually selectable PCAP/CSV files and provenance. Nothing is preloaded.
- `script.md`: 3-minute-20-second video narration.

Reports are encrypted and decrypted **inside the app**. The one-time report key must be shared separately from the encrypted JSON. The built-in Validation Engine's local sandbox check works after a case produces a forecast. The optional Strix-controlled scan is not active in this bundle because the Strix CLI and LLM provider are not configured; the local check does not verify model accuracy or retrain the checkpoint.

The service binds only to `127.0.0.1`. Its Compose configuration passes the host Docker socket into the app container for the optional controlled-validator integration. Access to that socket gives the container substantial control over the host Docker daemon; run this bundle only on a trusted machine. Windows app logs are at `%LOCALAPPDATA%\CYBERMIND\launcher.log`.
