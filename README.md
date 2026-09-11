<div align="center">

### SIH26 — CYBERMIND

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
├── CYBERMIND_REAL/           # Core implementation
│   ├── src/cybermind/        # Source modules (models, data, evaluation)
│   ├── scripts/              # Training, evaluation, and data preparation
│   ├── configs/              # Configuration files (gb10_full.yaml)
│   ├── data/                 # Raw, intermediate, and processed data
│   ├── checkpoints/          # Model checkpoints
│   ├── docs/                 # Documentation and reports
│   ├── tests/                # Unit tests
│   └── examples/             # Synthetic correctness checks
├── multisource_audit/        # Audit pipeline and verification scripts
├── session_backup_tools/     # Automation scripts for context generation
└── SESSION_CONTEXT.md        # Complete session history and handoff document
```

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

- `CYBERMIND_REAL/README.md` - Detailed implementation guide
- `CYBERMIND_REAL/docs/PHASE01_FINAL_REPORT.md` - Phase 1 verification checklist
- `CYBERMIND_REAL/docs/PUBLIC_DATA_SOURCES.md` - Public dataset registry
- `SESSION_CONTEXT.md` - Complete session history and architecture rationale

---

<div align="center">

Built by Team Untangle
</div>
