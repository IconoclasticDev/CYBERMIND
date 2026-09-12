# Final implementation plan — Phase 2 audit

Completed 2026-09-12 against Phase 1 commit `4772f70`. Phase 2 exit criteria passed. Phase 3 requires separate user approval and has not started.

## Changes delivered

- **2.1 Policy:** `knowledge/stage_mapping.yaml` now defines forward/stay transitions for stages 0–5, explicit campaign resets backwards into 0/1, and unrestricted transitions into/out of Unknown/Ambiguous (6).
- **2.2 Decoder:** new `StageDecoder` implements a learned linear-chain CRF and constrained Viterbi decoding. Both partition computation and decoding apply hard negative-infinity masks. Computation uses fp32; policy masks persist as checkpoint buffers. The existing StageHead is unchanged.
- **2.3 Training:** `loss.use_crf_stage` defaults to false. When enabled, separately logged `crf_stage` loss is added alongside existing stage cross-entropy, with weight `loss.crf_stage` (defaulting to the existing stage weight; smoke uses 0.5). Illegal supervised transitions raise a clear error.
- **2.4 Inference:** Python forecasts, rollouts, evaluation and app output use constrained decoded stages when enabled. Checkpoint constructors in evaluation, app, counterfactual, visualization and ONNX loading reconstruct the CRF setting. Existing stage-logit output remains available; CRF forecast decoding consumes ensemble-mean raw StageHead emissions.
- **2.5 Metric:** illegal-transition counts and rates pool pairs within individual sequences, without joining unrelated scenarios. Only explicitly declared, policy-permitted backward resets are excluded from the denominator.

Reset declarations belong to the destination timestep: training reads boolean `GraphState.metadata["campaign_reset"]`; decoding accepts an explicit boolean reset mask. Resets are never inferred from labels or predictions. A declaration permits only the documented reset edges, not arbitrary backwards movement. Missing declarations default to false. Future data preparation must supply actual campaign boundaries; the decoder does not infer them from CSV input.

With the CRF disabled, no CRF parameters are constructed, legacy parameter initialization remains compatible, and decoding follows the existing argmax path. Working smoke flags remain off; enabled verification uses its own configuration and output paths.

## Exit evidence

Evidence is in `examples/phase2_stage_decoder/`, with commands and runtime recorded in `verification_status.json` and individual measurements in `execution_matrix.json`.

- Full suite: **94 passed, zero skipped** on Python 3.14.7 / Torch 2.14.0+cu130 / PyG with the RTX 5060 Laptop GPU. The run reported 903 warnings; these did not fail the checks.
- All six required cases passed: finite decoder loss/gradients, adversarial decoding, and actual training/forecast integration, each on CPU and CUDA.
- Decoder transition gradient norms: CPU **1.313083**, CUDA **1.164321**. Joint training transition gradient norms: CPU **0.593164**, CUDA **0.593035**. Emission and stage-head gradients were also verified; forbidden transitions receive no gradient.
- Adversarial independent argmax had illegal rate **2/3**, while constrained decoding had **0** on both devices. Its decoded path was `[4, 6, 0, 1]`: this is legal because Unknown (6) is explicitly exempt. This demonstrates policy enforcement, not strict monotonicity across Unknown or useful predictive diversity.
- Tests also cover exhaustive small-state partition/Viterbi references, explicit resets, padding, validation errors, batched rollout axes, checkpoint flag handling, disabled behavior and explanations under inference mode. CPU/CUDA random inputs differ; their loss values are not claimed as numerical parity evidence.

The isolated one-epoch CPU CRF smoke used the frozen synthetic tensors, edge features off, CRF on, and zero dataloader workers. It saved and reloaded `checkpoints/phase2_crf.pt`, including the CRF flag and policy buffers.

| Measurement | Training | Validation |
| --- | ---: | ---: |
| Total loss | 3.874246 | 1.561869 |
| Unweighted CRF loss | 5.995313 | 3.271163 |

Held-out evaluation reported illegal-transition rate **0 over 3 pairs**. F1, precision and recall were 0, and AP was 1/3. These tiny synthetic results establish execution correctness only, not detection performance.

The frozen Phase 0 checkpoint's existing evaluation fields matched within **1e-6**; new decoding/transition fields are additive. All **49** frozen baseline evidence files and the baseline manifest remained byte-identical. Manifest SHA-256: `46be0cc83ad87bf462b9c661e6b55935b90427d3e80311287ffff91c7572e90b`. Phase 1 evidence was not regenerated.

## Limits and next approval gate

ONNX checkpoint loading supports the CRF-enabled model, but the exported wrapper still emits raw logits; constrained decoding is implemented in Python, not embedded in the ONNX artifact. No later deployment phase is claimed complete.

Phase 3 must exercise all four feature combinations together, check explicit reset declarations in its synthetic fixtures, and assess prediction diversity/Unknown usage. A correct constrained decoder should report zero illegal transitions; the plan's nonzero condition should be addressed with a separate diversity check rather than introducing illegal predictions.

No heavy datasets were acquired, no full training was performed, and no Phase 3 work was started. Full CIC-IDS2018 remains deferred to Phase 5 on GB10 per the user's correction. Changes and evidence are committed locally only; nothing is pushed.
