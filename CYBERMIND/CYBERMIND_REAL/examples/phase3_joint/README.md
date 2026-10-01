# Phase 3 evidence — incomplete diversity gate

`audit_status.json` is the final gate assessment: 384 passing test executions and passing regression/memory checks, but **prediction diversity did not pass**. `verification_status.json` records the original matrix commands and says checks completed pending audit; it must not be interpreted as a Phase 3 pass.

- `run_verification.py`: four full-suite runs selected through the joint tests' flag environment variables, four CPU pipeline integrations, frozen regression and combined GPU integration.
- `run_combined_smoke.py`: two-epoch combined GPU check using an isolated copy of `configs/smoke.yaml` and the frozen synthetic tensors.
- `diagnose_stage_diversity.py`: read-only selected/final checkpoint comparison of raw emissions and decoded predictions.
- `audit_verification.py`: validates exact joint cases, regression, finite two-epoch GPU runs, memory and the unresolved diversity gate.
- `pytest_*.xml` / logs and `execution_matrix.json`: original matrix evidence.
- Each variant directory contains configuration, generated fixture/provenance, logs, history, evaluation and memory report. Locally retained processed tensors and checkpoints are ignored by Git and fingerprinted in the manifest.

Run the model runners with the project CUDA-enabled `.venv/Scripts/python.exe` from the project root. The audit runner only needs standard-library Python. These runners overwrite their own Phase 3 outputs; preserve this snapshot or use a separate copy before rerunning, then regenerate the manifest. Generated configs record absolute local output paths.

All data are synthetic, including rows routed through the CIC-IDS2018 corpus adapter. No reported metric establishes real-corpus detection quality. See `../../docs/FINAL_PLAN_PHASE3_AUDIT.md` and the execution checklist before proceeding; Phase 4 requires a passed Phase 3 gate and separate approval.
