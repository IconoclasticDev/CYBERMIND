# Phase 2 verification evidence

This directory records constrained stage-decoder verification on 2026-09-12. All model data are synthetic frozen Phase 0 fixtures; these results are not real-corpus quality measurements.

- `verification_status.json`: commands, runtime, checkpoint checks and frozen-baseline integrity results.
- `pytest.log` / `pytest.xml`: full suite, 94 passed and zero skipped.
- `execution_matrix.json`: six CPU/CUDA exit cases, including gradient norms and adversarial decoding.
- `cpu_precheck.log`: earlier CPU-only check (22 passed, three CUDA cases skipped); the full CUDA-enabled run above supersedes it.
- `legacy_eval.json`: legacy checkpoint comparison; existing fields matched within 1e-6.
- `crf_smoke.yaml`, `train_history.json`, `crf_eval.json` and accompanying logs: isolated one-epoch CPU training and checkpoint reload.
- `manifest.json`: SHA-256/size inventory of evidence, implementation sources and locally retained checkpoint files. Checkpoints are ignored by Git.

The adversarial path `[4, 6, 0, 1]` is legal through the policy's Unknown exemption. Zero illegal rate is not a prediction-diversity or detection-quality claim. See `../../docs/FINAL_PLAN_PHASE2_AUDIT.md` for the full audit and limitations.

To repeat verification from the project directory with its CUDA-enabled `.venv` available, run `.venv/Scripts/python.exe examples/phase2_stage_decoder/run_verification.py`. This rewrites Phase 2 outputs and its local checkpoint; regenerate the evidence manifest after any rerun. It verifies and does not overwrite the frozen Phase 0 baseline. Phase 3 remains subject to user approval.
