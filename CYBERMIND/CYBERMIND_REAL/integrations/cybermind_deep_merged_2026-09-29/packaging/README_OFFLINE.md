# CYBERMIND offline Windows bundle

Double-click **CYBERMIND.exe** in File Explorer. The launcher verifies and loads the bundled Docker images on first use, starts the local containers, waits until `best.pt` is available, and opens `http://127.0.0.1:8000/` in your default browser. The independent decrypter is at `http://127.0.0.1:8001/` and also at `/incident-decrypter` in the app. All app ports bind to localhost.

This is an EXE **launcher for a Docker application**, not a replacement for Docker Engine. Windows 10/11 x64, virtualization, WSL 2, and Docker Desktop with Linux containers must be installed and able to start. Install those prerequisites once before going offline. If Docker Desktop is stopped, the launcher tries to start it and waits up to two minutes. The first launch loads the verified image archives and can take several minutes. Later launches reuse installed images and the persistent `cybermind_data` Docker volume. No network connection is needed to run the bundled images, inference, local NLP chatbot, or report encryption/decryption.

Keep `CYBERMIND.exe`, `compose.offline.yaml`, and the `images` directory together. The EXE alone is not a complete app. `images/manifest.json` pins the size and SHA-256 of each image archive. The launcher verifies an archive before loading it; Docker images already present under the matching tags are reused. Logs are written to `%LOCALAPPDATA%\CYBERMIND\launcher.log`.

Use the `demo` directory from the File Explorer upload picker for a real PCAP or flow CSV. The CTU IoT-23 PCAP is a raw-ingestion demo, not an accuracy benchmark for the CIC-IDS2018-trained checkpoint. The model is `best.pt` in the bundled app image. The report decrypter is a separate local container and HTML tool; share the one-time report key separately from an encrypted report file.

The data assistant uses its bundled, offline question router. The built-in **Run local check** works after a capture or sample has produced a forecast; it records four responses from the bundled in-process demonstration target. This is a sandbox-behavior check, not an independent attack-stage label or a model-accuracy test.

**Run controlled validation** is a separate Strix scan and remains unavailable in this offline bundle. The image does not include the Strix CLI, a Docker CLI/socket accessible to that CLI, a live target service at `127.0.0.1:8081`, or a configured Strix LLM provider. Installing Docker Desktop on the host does not automatically provide those dependencies inside the app container. Forecasts and demo analysis remain available. The image uses CPU inference, so throughput depends on the host machine.

To stop the containers, run `docker compose -p cybermind-offline -f compose.offline.yaml down` in this directory. The named data volume remains; `down` does not delete it.

## Linux x86-64 Docker launch

The image archives are Linux/amd64. From this extracted directory, with Docker Engine and Compose installed, run:

```sh
docker load -i images/cybermind-offline-app.tar
docker load -i images/cybermind-offline-decrypter.tar
docker compose -p cybermind-offline -f compose.offline.yaml up -d --no-build --pull never
```

Open `http://127.0.0.1:8000/` for the app and `http://127.0.0.1:8001/` for the independent decrypter. This path runs from bundled images without a download. The Windows `CYBERMIND.exe` in this Docker bundle is only a launcher; the separate native desktop EXE is the Windows no-Docker option.
