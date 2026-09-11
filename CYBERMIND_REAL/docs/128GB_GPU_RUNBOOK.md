# 128-GB GPU runbook

## One command

```bash
cd CYBERMIND_REAL
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel setuptools
pip install -r requirements.txt
./scripts/run_training_from_zero.sh
```

If CIC-IDS2018 is not already present:

```bash
CYBERMIND_DOWNLOAD_CIC2018=1 ./scripts/run_training_from_zero.sh
```

The first invocation performs preflight, normalization, strict validation, graph construction, leakage-safe split, baseline evaluation, model training, validation/test evaluation and result packaging.

## Recommended operational sequence

```bash
nvidia-smi
python scripts/gpu_preflight.py --config configs/gpu_128gb.yaml
python scripts/collect_knowledge.sh
CYBERMIND_DOWNLOAD_CIC2018=1 ./scripts/run_training_from_zero.sh
```

Do not use the full dataset blindly if local disk is insufficient. Start with a dated/scenario prefix, prove the pipeline, then scale to the intended corpus.

## Resume

The launcher accepts the training checkpoint:

```bash
CYBERMIND_RESUME=checkpoints/best_128gb.pt ./scripts/run_training_from_zero.sh
```

## Controlled first production run

Before a long experiment, use:

```bash
CYBERMIND_EPOCHS=1 ./scripts/run_training_from_zero.sh
```

Confirm GPU memory, loss movement, checkpoint creation and evaluation output. Then launch the full configured run.

## After training

```bash
python scripts/eval.py --config configs/gpu_128gb.yaml --checkpoint checkpoints/best_128gb.pt --split test
streamlit run scripts/app.py
```

Never report synthetic smoke metrics as cyber-dataset benchmark results.
