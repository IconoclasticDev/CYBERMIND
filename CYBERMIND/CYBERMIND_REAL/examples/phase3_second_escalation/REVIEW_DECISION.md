# Reviewed authorization and scope

On 2026-09-13 the user supplied `CYBERMIND_Frozen_Fixture_Gate_Decision.pdf` and instructed: **“execute this plan immidiately”**, following the explicit request for approval of the periodic experiment and a frozen-fixture choice. This instruction is recorded as authorization to execute the document's recommended Option 2 engineering path (Tasks A and B). The agent is not claiming that the PDF itself was an earlier signed decision.

- Frozen fixture: approved scoped gate revision to zero illegal transitions and finite/non-degenerate supervised loss, with gradient flow and retained regression checks. No diversity requirement applies to this fixture under the reviewed gate. Original failed diversity evidence remains unchanged.
- Integration fixture: approved derived sine/cosine inputs from each node's existing normalized coordinate `x[:,2]`, period 4 seconds. Original persisted tensors, raw coordinate, labels, splits and topology are unchanged; effective input width increases by two. This follows the supplied engineering prompt's per-node coordinate specification rather than the earlier proposal's graph-level broadcast.
- Integration exit gate: unchanged, independent future steps 1–4, at least two non-Unknown stages and zero illegal transitions at each step. Same original architecture except the authorized input width; same CRF policy, losses, training protocol and validation-F1 selection.
- Phase 4: prohibited until the resulting audit is reviewed, irrespective of diagnostic outcome. Protected `configs/gb10_*.yaml` files are outside this work.

The gate revision is justified by the frozen fixture's intended mechanical/regression scope and the user's execution instruction. The PDF's stronger claim that random features make prediction diversity mathematically impossible is not adopted: diversity is distinct from accuracy. No representation or training change is being made to the frozen fixture.

## Checklist

- [x] Record authorization, scope, exact gate revision and evidence qualification.
- [x] Add isolated frozen-gate evaluator that leaves historical evidence untouched.
- [x] Implement default-off fixed periodic representation with checkpoint configuration validation.
- [x] Focused CPU transform tests: raw preservation, periodic extrapolation, checkpoint reload and invalid constants.
- [x] Complete diagnostic #6: selected epoch 94 fails diversity at steps 1–3; final epoch 100 passes all four steps. No selected-checkpoint substitution.
- [x] Verify revised frozen gate against original evidence: PASS without further training or input changes.
- [x] Complete CPU/CUDA regression matrix: 524 test executions, zero skips; baseline comparisons and hash preservation pass. Published `PHASE3_SECOND_ESCALATION_AUDIT.md`.
- [ ] Prove Phase 3 exit criteria met under this reviewed scope.
