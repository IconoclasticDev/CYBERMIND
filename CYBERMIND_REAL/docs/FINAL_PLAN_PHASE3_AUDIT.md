# Final implementation plan — Phase 3 audit

Date: 2026-09-12. Base commit: `555c219`. User approved Phase 3 with "continue". **Phase 3 is incomplete: the prediction-diversity gate remains unmet. Phase 4 is not authorized and has not started.**

## Work delivered

- Extended `scripts/phase01_smoke.py` with explicit edge/CRF flags, CPU/CUDA selection, isolated output/checkpoint directories, and protection against overwriting the frozen baseline directory.
- Added `scripts/phase3_train_measure.py`, which executes the real training entrypoint in the measured process and records peak CUDA allocated/reserved memory against the runtime-reported device capacity. This measures the PyTorch allocator, excluding other applications and driver allocations.
- Added joint training/forecast/checkpoint tests for all four flag combinations on CPU and actual CUDA. Enabled edge projections and CRF transitions require finite, nonzero gradients; strict checkpoint reload preserves forecast output.
- Added reproducible matrix, smoke, diagnosis and evidence-audit runners under `examples/phase3_joint/`.
- Declared synthetic campaign resets from the fixture's generation clock after data preparation: each scan at second modulo four equal to zero is an independent campaign, with the following second declaring its reset. Only the newly generated CRF fixtures receive this metadata. Features, labels and frozen inputs are unchanged. Training consumes these declarations; forecast evaluation uses the default policy without future reset declarations.

## Verification results

| Edge features | CRF | Full suite | CPU pipeline |
| --- | --- | --- | --- |
| Off | Off | 96 passed, 0 skipped | Two epochs and 25-sample evaluation passed |
| On | Off | 96 passed, 0 skipped | Two epochs and 25-sample evaluation passed |
| Off | On | 96 passed, 0 skipped | Two epochs and 25-sample evaluation passed |
| On | On | 96 passed, 0 skipped | Two epochs and 25-sample evaluation passed |

These are **384 test executions**, not 384 distinct tests. `audit_status.json` validates the exact eight joint CPU/CUDA cases, their flag values, enabled gradient norms and strict checkpoint reload results. Existing library warnings were recorded; no tests were skipped or failed.

The freshly trained both-off pipeline reproduces the frozen Phase 0 integration evaluation and training history within **1e-6**, including original per-sample fields. Separately, evaluation of the frozen baseline checkpoint matches its original report within the same tolerance. New decoding metrics are additive. All **49** frozen files and their manifest remain unchanged.

Two additional both-on CUDA runs completed:

| Configuration | Epochs | Peak allocated | Peak reserved | Result |
| --- | ---: | ---: | ---: | --- |
| Phase 0.1 integration fixture | 2 | 70,297,600 bytes | 92,274,688 bytes (88 MiB) | Finite train/validation losses |
| `configs/smoke.yaml` frozen tensors | 2 | 74,547,200 bytes | 75,497,472 bytes (72 MiB) | Finite train/validation losses |

Both are below runtime-confirmed **8,518,041,600 bytes** of device memory. The second run uses an isolated copy of the smoke configuration with both flags enabled and zero workers to limit host RAM; working configuration and frozen tensors are unchanged. Integration retains its existing zero-worker setting.

## Unmet criterion and diagnosis

The PDF's Phase 3.3 says illegal-transition rate must not be identically zero or one. This conflicts with Phase 2's hard mask and explicit zero-illegal adversarial criterion: successful constrained decoding is expected to yield zero illegal transitions. Changing the decoder to introduce illegal transitions would violate the preceding phase.

We therefore measured stage diversity independently, without modifying emissions, seeds, labels or checkpoints to manufacture a pass. That check exposed a real limitation:

- Legacy both-off integration: all 50 decoded positions are Benign (0).
- Combined CPU and GPU integration: all 50 positions are Reconnaissance (1).
- Combined original smoke configuration: all six positions are Benign (0).
- Unknown-stage usage is zero in these combined checks. Varying infiltration risk does not resolve single-stage predictions.

`collapse_diagnosis.json` compares ensemble-mean raw StageHead emission argmax with Viterbi output. Both already predict the same single stage, including the final-epoch checkpoints. The mask is not introducing the observed lack of diversity. This is evidence of insufficient stage learning in these two-epoch synthetic runs, not a guarantee that the architecture is correct for real data.

The integration training supervision contains 184 Benign and 60 Reconnaissance positions; the original smoke supervision contains 102 Benign, 12 Initial Access and 12 Exfiltration positions. The unchanged checkpoint-selection policy optimizes validation infiltration F1, not stage accuracy. Checking the last checkpoints rules out selection alone as the explanation. No training hyperparameters or labels were tuned to make the gate pass.

## Proposed corrective scope for user decision

Keep the existing regression fixtures and all recorded failures. Amend Phase 3.3 to require **zero illegal transitions plus at least two non-Unknown predicted stages** on a separate balanced synthetic stage fixture with explicit feature signals and known campaign boundaries. Train and evaluate the combined model for two epochs, using separate train/validation/test samples and fixed generation seeds; report the actual outcome even if it fails. Retain the CPU/GPU gradient, checkpoint, finite-loss and VRAM checks.

This is a proposed adjustment to the supplied plan, not completed work. No balanced replacement fixture has been generated and Phase 4 remains closed. If the user requires the literal PDF condition, the contradiction must be resolved before a truthful pass can be recorded.

All runs used generated or previously frozen synthetic data. No new datasets were downloaded, no GB10 training occurred, no Phase 4 configuration work was started, and nothing was pushed remotely. Full primary-corpus download remains deferred to Phase 5 on GB10.
