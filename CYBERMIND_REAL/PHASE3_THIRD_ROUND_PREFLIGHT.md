# Phase 3 third-round preflight

**Resolved:** the subsequent reviewer decision specified tolerance 0.05 and validation stage CE, and authorized extension. The implemented protocol selects a passing epoch-185 checkpoint. See `PHASE3_FINAL_AUDIT.md`; the pending entries below preserve the original pre-decision record.

Source: `C:/Users/as030/Downloads/CYBERMIND_Phase3_Third_Round_Decisions.pdf`. User instruction: “execute all the actions mentioned in this pdf file.” Inspected current worktree at `2d5b6a8`.

## Required reviewer parameters

The document recommends Option 2, retaining validation infiltration F1 as the primary eligibility gate and choosing better validation stage quality within an explicitly specified tolerance. It instructs engineering: **“Do not choose or tune these yourself.”** No numeric tolerance or stage-quality tie-break metric is supplied in the PDF or the user's execution instruction.

- Absolute F1 tolerance (0–1): **not supplied**.
- Validation stage-quality tie-break metric: **not supplied**.
- No tolerance has been tested against the existing history, and no checkpoint has been selected under a proposed rule.
- Known disclosed comparison: epoch 94 F1 = 1.0; epoch 100 F1 = 0.9230769231; gap = 0.0769230769. These values are not a basis for the agent to invent an acceptable tolerance.

## Verified readiness and checkpoint limitation

The existing diagnostic #6 history contains all 100 epochs and validation fields `f1`, `stage` (StageHead cross-entropy), `crf_stage`, and other losses. A reviewer-specified rule can therefore be applied to that history without new training and without test data.

Only two checkpoint files were retained: `combined.pt` (epoch 94) and `combined_last.pt` (epoch 100). The active loop overwrites the best and last files; it does not save every epoch. If the approved validation-only rule selects another epoch, the metrics alone cannot reconstruct its weights. That checkpoint must be reproduced from the original seed/config, with validation-history parity checked, before independent four-step evaluation. It must not be replaced with the nearest saved epoch.

For the real training path, selection implementation must retain enough eligible candidates to recover the true stage-quality optimum when the best observed F1 increases and the eligibility band narrows. Saving only the currently selected checkpoint can lose an earlier candidate that later becomes optimal. This correctness requirement will be addressed without altering the default legacy policy.

## Execution checklist

- [x] Read all three PDF pages and distinguish recommendations from supplied parameter decisions.
- [x] Verify the full validation history and available checkpoint files.
- [x] Inspect actual training-loop selection and retention logic.
- [ ] Record the reviewer’s exact option, tolerance and stage-quality metric before applying the new rule.
- [ ] Implement the approved policy with explicit configuration and default-off compatibility.
- [ ] Apply it only to the existing 100-epoch validation history and report the selected epoch.
- [ ] Independently evaluate that exact checkpoint at all four original integration steps; reproduce missing weights if necessary.
- [ ] Run the four-flag regression suite and verify all historical evidence hashes.
- [ ] Publish the actual Phase 3 verdict. Phase 4 remains closed.
