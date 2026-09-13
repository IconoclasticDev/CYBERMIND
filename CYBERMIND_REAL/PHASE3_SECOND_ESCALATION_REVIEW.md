# Phase 3 second escalation — concrete reviewer decisions

**Status update:** the subsequent user instruction “execute this plan immidiately” with `CYBERMIND_Frozen_Fixture_Gate_Decision.pdf` authorizes its Option 2 engineering path. See `examples/phase3_second_escalation/REVIEW_DECISION.md` for the execution decision. The pending entries below are the preserved pre-decision proposal, not the current authorization state.

Source: `C:/Users/as030/Downloads/CYBERMIND_Phase3_Second_Escalation.pdf`, pages 1–2. Inspected current worktree at `b068bd2`. Phase 3 remains failed; Phase 4 is closed.

## Decision A: periodic-feature diagnostic #6

The PDF sequencing step 1 says: “Confirm with a reviewer that a derived periodic feature on the unmutated integration coordinate does not count as a fixture change.” The prior user instruction forbids unilateral fixture/gate substitutions. General authorization to follow this plan does not resolve its explicitly reserved reviewer decision.

Proposed experiment for approval:

- Preserve all original integration tensors, labels, topology, splits and historical evidence. Create isolated diagnostic outputs.
- Append two derived node-input dimensions, sine and cosine of the existing graph clock coordinate, alongside all original 34 dimensions. Effective model inputs therefore change from 34 to 36 dimensions; original persisted inputs remain untouched. This is disclosed feature engineering, not an unchanged-input experiment.
- Use the same audited graph coordinate `state.x[0,2]` (`bytes_total`) for the graph's clock and broadcast the two derived values to its nodes. Define `seconds = (coordinate - intercept) / slope` and `angle = 2*pi*seconds/4`. The existing training-only fit gives slope `0.02793721242224979` and intercept `-1.7181385639683615`. Recompute and persist these constants from training only; verify them against prior evidence. Period 4 is explicitly specified by this escalation plan and supported by the earlier training-label diagnostic. No validation/test labels or future labels enter this transformation.
- Apply the identical fixed transform in training, validation, checkpoint reload and forecasting. Default-off behavior must preserve the original model path and old checkpoints.
- CPU-only, seed 42, original combined configuration and loss coefficients, LR 0.001, batch 16, accumulation 2, 100 epochs, patience 101. This matches the previous exposure diagnostic. Keep validation infiltration F1 checkpoint selection; report selected and epoch-100 checkpoints separately. No test-driven hyperparameter retries.
- Retain the exact independent four-step requirement: at least two non-Unknown predicted stages, fewer Unknowns than samples, zero illegal incoming transitions at each step. Keep raw per-step emissions, transition values and argmax logs. No future oracle resets or prototype replacement fixture.
- Audit all four feature-flag regression contexts, original input hashes, transform/checkpoint consistency and actual learned-model results. A passing analytical clock rule is not a passing model.

Decision A status: **PENDING explicit reviewer approval of the derived-feature input change under the retained gate.** No diagnostic #6 training has started.

## Decision B: frozen smoke fixture

PDF sequencing step 3 reserves an explicit written reviewer decision between:

1. **Regenerate the fixture with stage-conditioned signal.** This is a fixture change; preserve the original failed evidence and separately identify the new data, assumptions and split construction. Exact generator details would need review before any run.
2. **Revise this fixture's gate only.** Retain finite-loss/gradient, legal-decoding, checkpoint and regression checks; remove its stage-diversity requirement. The integration fixture retains the full four-step diversity requirement. This is a gate revision and conflicts with the earlier no-loosening instruction unless the reviewer explicitly supersedes it.

A third permissible reviewer response is to retain the original frozen gate and decline both changes; in that case this escalation plan does not establish an overall Phase 3 pass.

**Evidence qualification:** the PDF overstates the frozen fixture finding. Conditional random feature distributions do not supply intended label discrimination, but they do not prove that diverse model predictions are impossible. Diversity is not accuracy; a model can output different stages without useful label generalization. Node-count attack proportions also vary in the finite training sample. No impossibility theorem or guaranteed diagnostic outcome has been established. Any gate revision must rest on the intended scope of this fixture, not on a false proof that diversity cannot occur.

Decision B status: **PENDING.** No further frozen-fixture training, regeneration or gate revision will occur before that decision.

## Execution checklist

- [x] Read second escalation PDF and inspect current source and original diagnostic evidence.
- [x] Specify the proposed input transform, constants, training budget, unchanged integration gate and verification scope.
- [x] Flag the difference between label learnability and output diversity.
- [ ] Receive Decision A.
- [ ] Implement and verify default-off periodic input support after approval.
- [ ] Run CPU diagnostic #6 and audit selected/final checkpoints at all four steps.
- [ ] Receive Decision B and record exactly which earlier constraint, if any, is superseded.
- [ ] Execute the authorized frozen-fixture decision and its verification.
- [ ] Publish a requirement-by-requirement Phase 3 re-audit with actual evidence.
- [ ] Prove all authorized Phase 3 exit criteria met. Currently unproven; no Phase 4 work.
