# Approved Phase 3 balanced-fixture evidence

Status: **passed under the user-approved revision**, 2026-09-12. The gate requires zero illegal transitions and at least two non-Unknown future stages. CPU and CUDA each produced all six stages, eight future predictions per stage, over 48 test samples.

This fixture deliberately encodes artificial class prototypes with independent jitter. It tests learnability and one-step stage diversity on constant-stage sequences; it is not network telemetry, realistic generalization, progression/reset learning or detection-quality evidence.

- `run_verification.py`: fixed fixture generation, split checks, actual two-epoch CUDA training, CPU/CUDA evaluation and preservation checks. It refuses to overwrite an existing training history.
- `fixture_manifest.json`: seeds, sample counts, target-stage balance and tensor hashes.
- `config.yaml`: isolated combined smoke configuration. Paths refer to this local project.
- `train_history.json`, `train_memory.json`, `train_cuda.log`: actual training and allocator measurements.
- `eval_cpu.json`, `eval_cuda.json` and logs: one-step evaluation of the validation-selected epoch-1 checkpoint from the two-epoch run.
- `verification_status.json`: commands and revised-gate results, including preservation of old evidence.
- `audit_status.json`: combined Phase 3 assessment, incorporating the earlier 384 passing test executions and baseline regression.
- `manifest.json`: exact-byte evidence/source inventory, with local tensors/checkpoints fingerprinted separately because Git ignores them.

Run with the project `.venv/Scripts/python.exe` and real CUDA. To perform another experiment, use a separate evidence-directory copy; do not overwrite this record or adjust the seed/configuration based on test results. The original `examples/phase3_joint/` failures and frozen baseline remain untouched.

See `../../docs/FINAL_PLAN_PHASE3_REVISED_AUDIT.md` for the completed audit and limitations. Phase 4 requires separate user approval.
