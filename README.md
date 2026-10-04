<div align="center">

# CYBERMIND

### Predictive Cyber Defence Platform

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-41CD52?logo=qt&logoColor=white)

</div>

## Overview

CYBERMIND helps analysts understand network activity and anticipate how an attack might develop. Built for **SIH26153: AI-based Network Attack Forecasting from Network Traffic Data**, it analyses uploaded traffic locally and works offline.

Upload a PCAP, PCAPNG or supported CICFlowMeter CSV file to explore host connections, view forecasts and compare possible defensive actions. The bundled PyTorch model uses GATv2, a temporal Transformer and latent dynamics to predict future risk and broad attack stages across network graph windows. Analysts can also ask questions about the loaded case, check sandbox responses, and encrypt or decrypt incident reports inside the app using AES-256-GCM.

Flow risk flags provide rule-based triage hints and are separate from the model's forecasts. Raw PCAP flows without labels remain unassessed in that table. The core application runs on a CPU without CUDA. Autonomous Strix scans need a separately configured CLI and LLM provider.

## Setup

### Run the packaged application

1. Install **Docker Desktop with Linux containers** on Windows, or **Docker Engine and Compose** on Linux x86-64. Start Docker and ensure your user can access it.
2. Clone this repository or download and extract its ZIP:

   ```sh
   git clone https://github.com/IconoclasticDev/CYBERMIND.git
   ```

3. From the repository folder:
   - **Windows:** double-click `CYBERMIND/START_WINDOWS.cmd`.
   - **Linux x86-64:** run `sh CYBERMIND/START_LINUX.sh`. Install `unzip` and `sha256sum`; the launcher opens Chromium as an app window when available, otherwise your default browser.
4. Upload your traffic file in the application to begin analysis.

The launchers verify and extract the [current offline release](CYBERMIND/releases/README.md), then load its bundled Docker image. No Python, Node.js or model training is needed. If the download contains a Git LFS pointer, first preparation needs internet to fetch the real release archive; Linux also needs `curl` or `wget`. For fully offline setup, transfer the complete release ZIP. Subsequent core operation needs no internet. Linux launch has not yet been verified on a Linux host.

### Build from the maintained source

The working application and build files are in [CYBERMIND_REAL](CYBERMIND/CYBERMIND_REAL/README.md). With Docker running, execute from the repository root:

```sh
cd CYBERMIND/CYBERMIND_REAL/integrations/cybermind_deep_merged_2026-09-29
docker compose up --build -d
```

Open `http://127.0.0.1:8000`. The initial source build requires internet for dependencies; use the packaged release for offline installation.
