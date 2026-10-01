# Frozen Phase 0 regression reference

Captured on 2026-09-12 from repository HEAD `70edd8f579452c735e0ac416fe3cbdef918b31a5`, using the final implementation plan's Phase 0 numbering.

All training/evaluation inputs here are **synthetic fixtures**, not downloaded CIC-IDS2018. These results establish software correctness and a regression reference; they are not detection-performance evidence.

- `config.yaml`: exact smoke configuration used for this capture.
- `processed/{train,val,test}.pt`: seeded synthetic fixtures (18/3/3 sequences).
- `train_history.json`: two completed CPU epochs with finite losses.
- `eval_test.json`: held-out smoke evaluation, three sequences.
- `baseline.pt`: validation-selected checkpoint; `baseline_last.pt`: epoch-two checkpoint.
- `integration/`: fresh outputs of the unchanged `scripts/phase01_smoke.py`, including 25 evaluated samples and automatic explanations. Historical project artifacts were restored after copying these outputs.
- `hardware.json`, `environment_packages.json`, `logs/`: runtime, bf16 operation, package versions, original test-suite output, and execution evidence.
- `execution_status.json`: includes the initial failed temporary-directory attempt and subsequent successful retry.
- `baseline_manifest.json`: byte sizes and SHA256 of frozen evidence; `.gitattributes` preserves exact bytes during Git checkouts.

The successful runtime was `.venv/Scripts/python.exe`, Python 3.14.7, PyTorch 2.14.0+cu130, PyG 2.8.0.post1. CPU arithmetic settings were `OMP_NUM_THREADS=2`, `MKL_NUM_THREADS=2`, `PYTHONHASHSEED=42`; the fixture and training seeds were 42, and the smoke dataloader used eight workers. GPU bf16 forward/backward was separately verified in that same environment. `logs/pytest_cpu_original.log` is an additional successful test run in the existing Python 3.12 CPU-only environment, not the training runtime.

Do not train directly with this archived configuration: its output paths describe the original capture. For Phase 3, reuse the frozen input tensors and mathematical settings, but write histories and checkpoints into a new run directory. The working `configs/smoke.yaml` now uses `examples/smoke/current/train_history.json` and `checkpoints/smoke.pt` to protect this baseline; these two output-path changes do not change model or loss settings.

`capture_baseline.py` returns without rerunning or overwriting a completed capture. Its freeze/resume guards were hardened after capture, without repeating or altering training. Knowledge snapshot acquisition is separate, in `acquisition/acquire_phase0_knowledge.py`, with provenance under `data/manifests/phase0_knowledge_manifest.json` and downloaded files under `knowledge/raw/`.

The main smoke model predicted no positives at threshold 0.5: precision, recall and F1 are zero. Preserve this result honestly for comparison; zero false-positive rate here is not evidence of useful detection quality. The composite loss can be negative because the existing Gaussian transition objective includes a log-variance term.
