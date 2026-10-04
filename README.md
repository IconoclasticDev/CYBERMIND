<div align="center">

# CYBERMIND

### Counterfactual World Model for Predictive Cyber Defence

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](#requirements)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](#technology-stack)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](#technology-stack)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.2%2B-EE4C2C?logo=pytorch&logoColor=white)](#technology-stack)
[![Docker](https://img.shields.io/badge/Docker-Desktop-2496ED?logo=docker&logoColor=white)](#option-1-prebuilt-docker-desktop-release)
[![Git LFS](https://img.shields.io/badge/Git-LFS-F64935?logo=git&logoColor=white)](#clone-the-repository)

</div>

---

## Overview

CYBERMIND is an offline predictive cyber-defence platform that models how network activity may evolve over time.

It combines graph neural networks, temporal modelling, multi-step forecasting, explainability, counterfactual intervention simulation, local case analysis, encrypted report export, and an analyst-facing React application.

Core capabilities include:

- Dynamic network-traffic graph construction
- GATv2 graph encoding
- Temporal Transformer modelling
- Multi-step attack-risk forecasting
- Attack-stage evidence and progression views
- Parallel future simulation
- Counterfactual actions such as host isolation and port blocking
- Attack Gravity and intervention-sensitivity analysis
- Local PCAP, PCAPNG, and supported CSV ingestion
- Evidence-linked analyst questions
- Encrypted case-report export and offline decryption
- Strix Attack Lab integration support
- Offline Docker and desktop operation

> CYBERMIND is a research and demonstration platform. Forecasts and validation results must not be treated as guaranteed attack attribution or containment effectiveness.

---

## Start here

After cloning or extracting the repository, install Docker and use one launcher:

- **Windows:** double-click `CYBERMIND/START_WINDOWS.cmd`.
- **Linux x86-64:** run `sh CYBERMIND/START_LINUX.sh`.

The launchers verify and extract the single current release automatically. They never require training, CUDA or a separate Python/Node setup. If a GitHub repository ZIP contains only a Git LFS pointer for the release, the first preparation downloads the real archive and checks its pinned hash. That initial download requires internet; later application launches use local files. For a fully offline transfer, bring the complete release ZIP rather than an LFS pointer.

## Recommended setup

The easiest way to run CYBERMIND is the canonical offline Docker Desktop release:

```text
CYBERMIND/releases/CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04.zip
```

This package includes:

- `CYBERMIND.exe`
- React frontend and FastAPI backend
- Pinned `best.pt` model checkpoint
- Offline Docker image
- Docker Compose configuration
- Windows and Linux launch/stop scripts
- Demonstration PCAP and CSV inputs
- Image and release integrity manifests

The Windows `CYBERMIND.exe` is a Docker-backed desktop launcher. Docker Desktop must be installed and running.

---

## Clone the repository

Large canonical deliverables are stored using Git LFS.

Install [Git](https://git-scm.com/) and [Git LFS](https://git-lfs.com/), then run:

```bash
git lfs install
git clone https://github.com/IconoclasticDev/CYBERMIND.git
cd CYBERMIND
git lfs pull
```

Without Git LFS, large release files may be downloaded only as small pointer files.

---

## Option 1: Prebuilt Docker Desktop release

### Windows 10 or 11

Requirements:

- 64-bit Windows
- Docker Desktop
- Docker Desktop Linux/WSL 2 engine
- Hardware virtualization enabled
- Sufficient free disk space for the extracted Docker image

Verify the downloaded release:

```powershell
Get-FileHash `
  ".\CYBERMIND\releases\CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04.zip" `
  -Algorithm SHA256
```

Expected SHA-256:

```text
1501067ff49208cbe1ca15e72bbef8a67f43c661a1cee9609d3e4eb7eb541e22
```

Extract the package:

```powershell
Expand-Archive `
  ".\CYBERMIND\releases\CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04.zip" `
  -DestinationPath ".\CYBERMIND\releases\CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04"
```

Then:

1. Start Docker Desktop.
2. Wait until Docker reports that the engine is running.
3. Open the extracted `CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04` folder.
4. Double-click `CYBERMIND.exe`.

Alternatively, start it from PowerShell:

```powershell
.\CYBERMIND.exe
```

On the first launch, CYBERMIND verifies and imports the bundled Docker image. This can take several minutes. Later launches reuse the imported image and persistent data volume.

Keep these items together:

```text
CYBERMIND.exe
compose.offline.yaml
images/
demo/
stop_windows.cmd
```

To stop CYBERMIND without deleting its persistent data:

```powershell
.\stop_windows.cmd
```

Windows launcher logs are stored at:

```text
%LOCALAPPDATA%\CYBERMIND\launcher.log
```

### Linux x86-64

Requirements:

- Linux x86-64
- Docker Engine
- Docker Compose plugin
- Optional Chromium or Chrome for an application-style window

Extract the release and enter its directory:

```bash
unzip CYBERMIND/releases/CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04.zip
cd CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04
```

Start CYBERMIND:

```bash
sh launch_linux.sh
```

Stop it without deleting persistent data:

```bash
sh stop_linux.sh
```

If Chromium or Chrome is available, CYBERMIND opens in an application-style window. Otherwise, the launcher opens the local URL in the default browser.

The supplied offline image supports Linux x86-64. Linux ARM64 and macOS images are not included in this release.

---

## Option 2: Build and run with Docker from source

Requirements:

- Docker Engine or Docker Desktop
- Docker Compose plugin
- Internet access during the initial image build

From the repository root:

```bash
cd CYBERMIND_REAL
docker compose -f compose.app.yaml build
docker compose -f compose.app.yaml up -d
```

Open:

- CYBERMIND: http://127.0.0.1:8000
- Offline incident decrypter: http://127.0.0.1:8001

View service status:

```bash
docker compose -f compose.app.yaml ps
```

View application logs:

```bash
docker compose -f compose.app.yaml logs -f cybermind
```

Stop the services:

```bash
docker compose -f compose.app.yaml down
```

To stop the services and also remove the persistent CYBERMIND data volume:

```bash
docker compose -f compose.app.yaml down -v
```

The `-v` command permanently removes data stored in the Compose volume. Use it only when a complete local reset is intended.

### Docker security note

The default Compose configuration does not mount the host Docker socket. The optional compose.strix.yaml override is only for separately configured external Strix integration.

Access to the Docker socket gives the container substantial control over the host Docker daemon. Run CYBERMIND only from a trusted checkout and on a trusted machine.

---

## Option 3: Native developer setup

This route runs the FastAPI backend and React application directly, without the prebuilt Docker image.

### Requirements

- Python 3.10 or newer
- Python 3.11 recommended
- Node.js 24 recommended to match the Docker build
- npm
- Git and Git LFS

### Windows PowerShell

```powershell
cd CYBERMIND_REAL

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Set-Location web
npm ci
npm run build
Set-Location ..

python scripts\launch_desktop.py
```

The launcher binds to a randomly selected loopback port and opens the application in the default browser.

If PowerShell blocks virtual-environment activation, use the environment’s Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Set-Location web
npm ci
npm run build
Set-Location ..

.\.venv\Scripts\python.exe scripts\launch_desktop.py
```

### Linux

```bash
cd CYBERMIND_REAL

python3.11 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cd web
npm ci
npm run build
cd ..

python scripts/launch_desktop.py
```

The native launcher uses:

```text
checkpoints/final_grouped/best.pt
web/dist/
examples/analyst_demo/
```

Local account data is stored under:

```text
~/.cybermind
```

Uploaded captures are temporary during parsing. Active case sessions remain in memory.

---

## Build the native Windows executable

This is separate from the Docker-backed executable included in the canonical release.

Prepare the Python environment and build the React frontend first:

```powershell
cd CYBERMIND_REAL

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

Set-Location web
npm ci
npm run build
Set-Location ..

.\scripts\build_windows_exe.ps1
```

The output is created at:

```text
CYBERMIND\CYBERMIND_REAL\dist\CYBERMIND\CYBERMIND.exe
```

Distribute the entire `dist\CYBERMIND` directory. The executable depends on the model, frontend, and runtime files bundled beside it.

Verify the resulting build on the target Windows version and architecture before distribution.

---

## Using the application

After CYBERMIND starts:

1. Create or unlock the local analyst account.
2. Select a bundled demonstration file or upload a supported local file.
3. Wait for parsing and graph construction to finish.
4. Review observed traffic, risk forecasts, and stage evidence.
5. Inspect the four-step forecast and Parallel Futures views.
6. Compare counterfactual interventions.
7. Run the built-in local validation check after a forecast is available.
8. Export an encrypted case report if needed.

Supported input categories include:

- `.pcap`
- `.pcapng`
- Supported packet-complete `.csv` files
- Bundled reproducible demonstration fixtures

A checkpoint that requires packet-level features rejects incompatible flow-only input instead of silently fabricating missing telemetry.

### Encrypted reports

CYBERMIND exports reports using AES-256-GCM encryption and a separate one-time key.

Keep the encrypted report and its key separate. Anyone possessing both can decrypt the report.

A decrypted HTML report is plaintext and should be handled as sensitive evidence.

---

## Optional Strix Attack Lab

The merged application and Strix integration source are located at:

```text
CYBERMIND/CYBERMIND_REAL/integrations/cybermind_deep_merged_2026-09-29/
```

The pinned optional Strix CLI archive is located at:

```text
tools/strix/strix-1.6.2-windows-x86_64.zip
```

Strix-controlled validation is not automatically enabled by the standard offline release. It additionally requires:

- The Strix CLI
- A supported LLM provider configuration
- An explicitly registered sandbox target
- Authorization to test that target

The core local validation path does not require Strix or an external provider.

Do not run controlled security validation against systems you do not own or have explicit permission to test.

---

## Model development and training

From `CYBERMIND_REAL` with the Python environment activated:

### Prepare data

```bash
python scripts/build_corpus.py \
  --source CIC-IDS2018 \
  --input data/raw/CIC-IDS-2018 \
  --output data/intermediate/CIC-IDS2018

python scripts/validate_dataset.py \
  --input data/intermediate/CIC-IDS2018 \
  --strict

python scripts/prepare_data.py \
  --config configs/gb10_full.yaml \
  --input data/intermediate/CIC-IDS2018 \
  --strict
```

### Run the GPU preflight

```bash
python scripts/gpu_preflight.py --config configs/gb10_full.yaml
```

### Train

```bash
python scripts/train.py \
  --config configs/gb10_full.yaml \
  --device cuda \
  --epochs 1
```

### Resume training

```bash
python scripts/train.py \
  --config configs/gb10_full.yaml \
  --device cuda \
  --resume checkpoints/best_gb10_last.pt
```

### Evaluate

```bash
python scripts/eval.py \
  --config configs/gb10_full.yaml \
  --checkpoint checkpoints/best_gb10.pt \
  --split val

python scripts/eval.py \
  --config configs/gb10_full.yaml \
  --checkpoint checkpoints/best_gb10.pt \
  --split test
```

### One-command training

```bash
./scripts/run_training_from_zero.sh
```

Enable the supported automatic CIC-IDS2018 download path:

```bash
CYBERMIND_DOWNLOAD_CIC2018=1 ./scripts/run_training_from_zero.sh
```

Resume from a checkpoint:

```bash
CYBERMIND_RESUME=checkpoints/best_gb10_last.pt \
  ./scripts/run_training_from_zero.sh
```

Override the epoch count:

```bash
CYBERMIND_EPOCHS=1 ./scripts/run_training_from_zero.sh
```

Automatic downloading does not solve missing packet-to-label alignment. Strict validation rejects datasets that do not satisfy the configured evidence requirements.

---

## Testing

### Core Python tests

```bash
cd CYBERMIND_REAL
python -m pytest tests -q -p no:cacheprovider
```

### Phase 0–1 smoke test

```bash
python scripts/phase01_smoke.py
```

### Root React application

```bash
cd CYBERMIND/CYBERMIND_REAL/web
npm ci
npm run build
```

### Merged application tests

```bash
cd CYBERMIND/CYBERMIND_REAL/integrations/cybermind_deep_merged_2026-09-29
python -m pytest tests -q -p no:cacheprovider
```

### Merged React frontend

```bash
cd CYBERMIND/CYBERMIND_REAL/integrations/cybermind_deep_merged_2026-09-29/frontend
npm ci
npm run build
```

Latest repository validation:

- Core Python tests: 244 passed
- Merged integration tests: 52 passed
- React production build: passed
- Canonical release SHA-256: verified
- Docker Compose configuration and referenced paths: validated

Docker itself is still required for an end-to-end container launch.

---

## Project structure

```text
repository/
├── CYBERMIND/
│   ├── START_WINDOWS.cmd       # Prepare and open the current application
│   ├── START_LINUX.sh          # Prepare and launch on Linux x86-64
│   ├── CYBERMIND_REAL/         # Research/training source and application integration
│   ├── deliverables/           # Final demo, architecture and verification records
│   ├── releases/               # One current runnable ZIP and source/training submission
│   └── tools/                  # Release launchers, verification and optional Strix tools
├── CYBERMIND Architecture Document.html
├── .gitattributes
├── .gitignore
└── README.md                   # Main guide
```

Generated environments, caches, extracted releases, local installers, build trees, raw massive datasets, and duplicate archives are intentionally excluded from Git.

---

## Technology stack

### Backend and modelling

- Python
- FastAPI
- Uvicorn
- PyTorch
- PyTorch Geometric
- NetworkX
- NumPy
- Pandas
- scikit-learn
- PyArrow
- ONNX and ONNX Runtime

### Frontend

- React 18
- Vite
- Lucide React

### Security and reports

- Argon2id password verification
- AES-256-GCM encrypted reports
- Trusted local checkpoint loading
- Loopback-only service binding

### Deployment

- Docker and Docker Compose
- PyInstaller
- Git LFS

---

## Documentation

Important documents include:

- `CYBERMIND Architecture Document.html`
- `CYBERMIND_Final_Implementation_Plan.pdf`
- `CYBERMIND/CYBERMIND_REAL/README.md`
- `CYBERMIND/CYBERMIND_REAL/docs/FASTAPI_REACT_APP.md`
- `CYBERMIND/CYBERMIND_REAL/docs/OFFLINE_ANALYST_APP.md`
- `CYBERMIND/CYBERMIND_REAL/docs/CYBERMIND_FULL_FINAL_IMPLEMENTATION_PLAN.md`
- `CYBERMIND/CYBERMIND_REAL/docs/SIH26153_TWO_PAGE_ARCHITECTURE.md`
- `CYBERMIND/CYBERMIND_REAL/docs/PUBLIC_DATA_SOURCES.md`
- `deliverables/architecture/`
- `deliverables/pdf/`

---

## Release integrity

Canonical release:

```text
CYBERMIND/releases/CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04.zip
```

SHA-256:

```text
1501067ff49208cbe1ca15e72bbef8a67f43c661a1cee9609d3e4eb7eb541e22
```

Manifest:

```text
CYBERMIND/releases/CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04.manifest.json
```

Always verify the ZIP before redistribution or demonstration.

---

## Troubleshooting

### Git downloaded only a tiny ZIP pointer

Run:

```bash
git lfs install
git lfs pull
```

### Docker Desktop is not ready

Start Docker Desktop and wait until the engine reports that it is running before opening `CYBERMIND.exe`.

### Windows first launch is slow

The first launch imports the bundled Docker image. Do not move or remove the adjacent `images` directory while this is happening.

### Port 8000 is already in use

For the source Compose deployment, stop the conflicting application or change the host-side port in `CYBERMIND/CYBERMIND_REAL/compose.app.yaml`.

The canonical packaged launcher selects an available loopback port automatically.

### React page is missing in native development mode

Build the frontend:

```bash
cd CYBERMIND/CYBERMIND_REAL/web
npm ci
npm run build
```

Then restart:

```bash
cd ..
python scripts/launch_desktop.py
```

### Model is unavailable

Verify this file exists:

```text
CYBERMIND/CYBERMIND_REAL/checkpoints/final_grouped/best.pt
```

If the repository was cloned without LFS, run:

```bash
git lfs pull
```

---

## Responsible use

CYBERMIND is intended for authorized defensive research, demonstrations, education, and analysis.

Use packet captures and validation targets only when you own them or have explicit authorization. Do not use the optional controlled-validation components against third-party systems without permission.

---

<div align="center">

Built by Team Untangle

</div>
