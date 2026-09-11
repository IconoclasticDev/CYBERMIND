# CYBERMIND automated training

## Single command

On the 128-GB GPU host, after cloning/extracting the package:

```bash
cd CYBERMIND_REAL
source .venv/bin/activate
./scripts/run_training_from_zero.sh
```

The launcher performs:

1. repository/readiness checks
2. CUDA/VRAM/PyG preflight
3. CIC-IDS2018 acquisition when explicitly enabled
4. corpus normalization
5. strict schema validation
6. graph/temporal sequence construction
7. leakage-safe train/validation/test split
8. logistic baseline
9. CYBERMIND training
10. validation/test evaluation
11. run artifact packaging

The only intentionally manual choice is whether to download very large datasets. Set `CYBERMIND_DOWNLOAD_CIC2018=1` when the host has enough disk/network capacity.

## Resume after interruption

```bash
CYBERMIND_RESUME=checkpoints/best_128gb.pt ./scripts/run_training_from_zero.sh
```

Use a specific checkpoint from your run when resuming; training scripts restore optimizer state and the recorded epoch.

## Quick smoke run

```bash
python scripts/make_synthetic.py --output data/processed/smoke.pt --num-sequences 64
./scripts/smoke_all.sh
```

The smoke path is not a benchmark; it verifies forward/backward/checkpoint/evaluation plumbing.

## Large public datasets

The package does not silently download multi-GB datasets into the archive. Use `collect_public_corpus.py` for acquisition and `data/manifests/public_collection_manifest.json` to record provenance. For sources whose official portal requires a web form/manual acceptance, supply the resulting direct URL through the documented environment variables or download into the source directory.
