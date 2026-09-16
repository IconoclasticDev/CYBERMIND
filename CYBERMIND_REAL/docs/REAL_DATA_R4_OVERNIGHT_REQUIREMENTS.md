# R4 overnight safeguards — requirements only, not authorization

Recorded from the user's 2026-09-16 instruction. **R4 has not started and is not
authorized.** Flag the proposed overnight run to the user before starting it.
Extra unattended runway applies to R4, never to R0 runtime setup.

- [x] Choose checkpoint cadence before the run. Use **N=1** (every epoch) to
  preserve the real-data plan's existing every-epoch requirement; keep failed
  checkpoints and save independently of validation improvement. Verify resume
  includes optimizer, epoch, scheduler/scaler where applicable, and RNG state.
- [x] Verify losses and validation metrics append incrementally to durable
  on-disk logs, flushed each epoch; stdout alone is insufficient. Retain errors
  and final status so morning review works even after process termination.
- [x] Predeclare early-stopping patience for actual chunk size and epoch budget;
  justify it before training. Neither default 10 nor inherited synthetic
  patience 101/201 is acceptable without a run-specific rationale.
- [x] Define and verify the first-observed single-stage-collapse stop condition
  before starting. Stop the run and report on that signal; no automatic restart,
  retuning, checkpoint substitution, or diagnostic retry loop overnight.
- [x] Separate safety monitoring from held-out test selection: predeclare the
  monitoring split, four-step decode and cadence; do not tune against final test
  gate results. Record the checkpoint and per-step histograms at any stop.
- [x] Check free disk, checkpoint retention, logging and bounded runtime, then
  present the concrete configuration and failure/stop behavior before R4 starts.

The fixed four-step exit check and validation selection policy remain unchanged.
**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.** Evaluation is still pending.
