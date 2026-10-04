# CYBERMIND

## Overview

CYBERMIND is an offline predictive cyber-defence platform for **SIH26153: AI-based Network Attack Forecasting from Network Traffic Data**.

Analysts upload PCAP, PCAPNG or supported CICFlowMeter CSV files. A pinned PyTorch model combines GATv2, a temporal Transformer and latent dynamics to forecast graph-window risk and coarse attack stages. The React/FastAPI application provides network visualisation, counterfactual defence comparisons, case-grounded questions, local sandbox checks, and AES-256-GCM report encryption with in-app decryption.

Flow-triage flags are separate from model forecasts; unlabeled PCAP flows remain unassessed. Core processing runs locally on CPU—CUDA is not required. Autonomous Strix scans require a separately configured CLI and LLM provider.

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
