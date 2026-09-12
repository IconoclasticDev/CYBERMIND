# Phase 1 verification evidence

Run `run_verification.py` with the project's CUDA-capable `.venv/Scripts/python.exe` from the project directory. It requires both CUDA and PyG and rejects skipped matrix cases. It does not download data or start another implementation phase.

- `edge_schema.json`: read-only probe of the existing graph builder after canonical preprocessing.
- `legacy_graph_encoder.py`: encoder source from Phase 0 commit `1d91b27`, used for actual old/new comparison.
- `legacy_compatibility.json`: all four backend/device comparisons, including rounding tolerances.
- `pytest.log`, `pytest.xml`, `execution_matrix.json`: all 69 tests and all eight required matrix cases, including per-layer gradient measurements.
- `legacy_eval.json`: evaluation of the frozen Phase 0 checkpoint with current flag-off code.
- `enabled_smoke.yaml`, `train_history.json`, `enabled_eval.json`: one-epoch synthetic training/checkpoint reconstruction check. Width is intentionally inferred from the seven-column legacy fixture; the matrix tests use the current 27-column schema.
- `verification_status.json`: runtime, executed commands, and exit outcomes.
- `manifest.json`: hashes of evidence and the implementation/tests as verified.

All data here is synthetic. Metrics are software-check evidence, not estimates of real-world detection performance. The one-epoch checkpoint remains locally at `checkpoints/phase1_edges.pt`, excluded from Git; its checksum is included in the manifest. The frozen Phase 0 files were read, never rewritten. An initial strict CUDA equality test failure is preserved separately for traceability.
