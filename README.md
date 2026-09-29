<div align="center">

### CYBERMIND

</div>

<div align="center">

[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)](#)
[![PyTorch](https://img.shields.io/badge/PyTorch-ee4c2c?logo=pytorch&logoColor=white)](#)
[![NumPy](https://img.shields.io/badge/NumPy-4DABCF?logo=numpy&logoColor=fff)](#)
[![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=fff)](#)
[![Scikit-learn](https://img.shields.io/badge/-scikit--learn-%23F7931E?logo=scikit-learn&logoColor=white)](#)

</div>

---

### Overview

CYBERMIND is a research-grade implementation of a counterfactual world model for predictive cyber defense. The system uses graph neural networks (GATv2) and temporal transformers to model network dynamics, predict infiltration probabilities, and simulate counterfactual interventions. It processes network traffic data to forecast attack stages, generate multi-hypothesis futures, and provide explainable risk assessments through gradient-based attribution.

---

### Project Structure

```text
SIH26/
├── CYBERMIND_REAL/                 # Authored product and research implementation
│   ├── src/cybermind/              # Model, data, evaluation, analyst and API modules
│   ├── web/                        # React application source
│   ├── integrations/               # Strix Attack Lab and merged desktop application
│   ├── scripts/                    # Training, inference, packaging and launch scripts
│   ├── configs/                    # Reproducible model/runtime configuration
│   ├── checkpoints/                # Required trained checkpoints
│   ├── docs/                       # Architecture, plans and technical guides
│   ├── tests/                      # Unit and integration tests
│   └── examples/                   # Reproducible demonstrations and fixtures
├── deliverables/                   # SIH documents, PDFs and final demo video
├── releases/                       # Tracked SIH package plus canonical Docker desktop ZIP
├── tools/strix/                    # Optional pinned Strix CLI archive
├── CYBERMIND_Final_Implementation_Plan.pdf
└── README.md
```


Generated environments, build trees, extracted release folders, installers, caches and raw authoring captures are intentionally excluded from Git.
---

### Tech Stack

- **Deep Learning**: PyTorch with PyTorch Geometric for graph neural networks
- **Graph Processing**: NetworkX for dynamic network graph construction
- **Data Processing**: NumPy, Pandas for numerical and tabular data manipulation
- **Machine Learning**: scikit-learn for baseline models and evaluation metrics
- **Visualization**: Matplotlib for rollout visualization and results plotting
- **Data Formats**: PyArrow for efficient data serialization, ONNX for model export

---

### Installation

```bash
cd CYBERMIND_REAL
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

For GPU training, ensure CUDA-compatible PyTorch is installed. The project requires Python >=3.10.

---

### Usage

#### Data Preparation

```bash
# Build corpus from CIC-IDS2018 data
python scripts/build_corpus.py --source CIC-IDS2018 --input data/raw/CIC-IDS-2018 --output data/intermediate/CIC-IDS2018

# Validate dataset quality
python scripts/validate_dataset.py --input data/intermediate/CIC-IDS2018 --strict

# Prepare training data
python scripts/prepare_data.py --config configs/gb10_full.yaml --input data/intermediate/CIC-IDS2018 --strict
```

#### Training

```bash
# Run GPU preflight check
python scripts/gpu_preflight.py --config configs/gb10_full.yaml

# Train model
python scripts/train.py --config configs/gb10_full.yaml --device cuda --epochs 1

# Resume training
python scripts/train.py --config configs/gb10_full.yaml --device cuda --resume checkpoints/best_gb10_last.pt
```

#### Evaluation

```bash
# Evaluate on validation set
python scripts/eval.py --config configs/gb10_full.yaml --checkpoint checkpoints/best_gb10.pt --split val

# Evaluate on test set
python scripts/eval.py --config configs/gb10_full.yaml --checkpoint checkpoints/best_gb10.pt --split test
```

#### One-Command Training

For production GPU hosts with prepared datasets:

```bash
./scripts/run_training_from_zero.sh
```

Enable automatic CIC-IDS2018 download:

```bash
CYBERMIND_DOWNLOAD_CIC2018=1 ./scripts/run_training_from_zero.sh
```

---

### Configuration

The main configuration file is `configs/gb10_full.yaml`, which controls:
- Graph construction parameters (node/edge features)
- Model architecture (GATv2 layers, Transformer dimensions)
- Training hyperparameters (learning rate, batch size, epochs)
- Data paths and preprocessing options
- Evaluation metrics and checkpoint settings

Environment variables:
- `CYBERMIND_DOWNLOAD_CIC2018=1` - Enable automatic dataset download
- `CYBERMIND_RESUME=checkpoint_path` - Resume from specific checkpoint
- `CYBERMIND_EPOCHS=N` - Override epoch count

---

### Features

- **Dynamic Network Graph**: Hosts as nodes, communication relationships as edges with rich feature representations
- **GATv2 Encoder**: Graph attention networks for spatial pattern recognition
- **Temporal Transformer**: Time-series modeling with positional encoding
- **K-step Rollout**: Multi-step future state prediction
- **Counterfactual Simulation**: Simulate interventions (Block Host, Isolate Host, Rate Limit)
- **Attack Gravity Scoring**: Risk reduction under isolation scenarios
- **Multi-hypothesis Futures**: Stochastic latent rollout generation
- **Explainability**: Gradient-based attribution for model decisions
- **Logistic Regression Baseline**: Comparison with traditional ML approaches
- **ONNX Export**: Portable model deployment for laptop inference

---

### Testing

```bash
# Run unit tests
python -m pytest tests -q -p no:cacheprovider

# Run Phase 0-1 smoke tests
python scripts/phase01_smoke.py
```

---

### Documentation

- `CYBERMIND_REAL/README.md` - detailed implementation and offline-app guide
- `CYBERMIND_REAL/docs/ARCHITECTURE.md` - model architecture
- `CYBERMIND_REAL/docs/CYBERMIND_FULL_FINAL_IMPLEMENTATION_PLAN.md` - preserved implementation plan
- `CYBERMIND_REAL/docs/SIH26153_TWO_PAGE_ARCHITECTURE.md` - submission architecture
- `CYBERMIND_REAL/docs/PUBLIC_DATA_SOURCES.md` - public dataset registry
- `deliverables/` - technical approach, editable document, PDFs and final demo video

### Canonical runnable release

The latest offline Docker Desktop package is:

```text
releases/CYBERMIND_DOCKER_DESKTOP_DEMO_READY_2026-09-30.zip
```

It includes `CYBERMIND.exe`, the offline Docker image, Compose configuration, Windows/Linux launch and stop scripts, demo inputs, integrity manifests and the pinned model. The ZIP is tracked with Git LFS; verify it against the adjacent manifest before distribution.

The source Docker application remains under `CYBERMIND_REAL/`, including `Dockerfile.app`, `compose.app.yaml`, and the merged integration Dockerfiles/launchers. The optional pinned Strix CLI archive is under `tools/strix/`; Strix still requires its own provider configuration and is not required for the core local validation path.

---

<div align="center">

Built by Team Untangle
</div>
