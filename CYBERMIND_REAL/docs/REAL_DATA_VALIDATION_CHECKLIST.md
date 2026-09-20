# Real-data validation checklist

Plan: `CYBERMIND_Real_Data_Validation_Plan.md`, supplied and authorized on 2026-09-16.
This is a separate R0–R6 sequence before main-plan Phase 5. Existing Phase 3/4
audits remain historical evidence. No GB10 run is authorized by this plan.

## R0 — COMPLETE; audited PASS

Reviewer update 2026-09-16: dates fixed to February 14 / March 1 / March 2;
Lateral Movement coverage amendment and exact malformed-source derivative
approved. R0 only is authorized. See `REAL_DATA_R0_REVIEWER_DECISION_2026_09_16.md`.

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.** Evaluation has not yet occurred.
Repeat this disclosure in every stage-coverage/illegal-transition artifact,
including R3–R6 and final architecture/novelty sections; never summarize it away.

- [x] Read the supplied plan and its referenced `CYBERMIND_CONTEXT.md`.
- [x] Preserve the earlier February 14 acquisition, failed regeneration, and strict-validation evidence.
- [x] Cross-check candidate stage coverage against primary-source documentation.
- [x] Rehash and register the failed February 14 precheck with explicit failure provenance.
- [x] Prevent failed custom extraction from publishing a final output filename; six focused tests pass.
- [x] Deliver `REAL_DATA_R0_AUDIT.md`; both proposals were subsequently approved and the derivative created.
- [x] R0.1 Freeze three dates and reviewer-approved coverage amendment.
- [x] Freeze precise capture membership for the remaining dates before acquisition (`capture_scope_frozen.json`).
- [x] Create and hash the approved 4,718,327-record February 14 derivative; verify byte-identical source prefix and unchanged original hash.
- [x] Replace the earlier 2–4-hour estimate with the user's fixed 60-minute feasibility / 90-minute hard cap.
- [x] Pin/download upstream source and retrieve runtime candidate metadata; installation/build/export not completed.
- [x] On continuation, honor the elapsed deadline; publish `REAL_DATA_R0_RUNTIME_RESULT.md` without resetting the timer.
- [x] Close executable CICFlowMeter runtime/schema attempt as NO-GO; reviewer-approved custom fallback applies and no third CICFlowMeter path is permitted.
- [x] Final bounded attempt: verified Java 8; pinned build failed on unresolved `org.jnetpcap:jnetpcap:1.4.1`; stopped without debugging or a third path.
- [x] Publish concrete CICFlowMeter NO-GO and record prior usage-limit interruption as tooling, not a CICFlowMeter result.
- [x] Assess fallback: existing 40-column exporter satisfies the implemented 20-field packet-feature contract in focused tests, but omits approximately 67 pinned CIC traffic statistics and differs in direction/session semantics.
- [x] Implement an unlabeled, atomic fallback R0 export path with explicit feature-gap provenance; the hardcoded schedule is not used during R0.
- [x] R0.2 fallback: export every frozen capture with full five-tuple/timestamps and all 20 project packet fields; attach the exact approximately-67-statistic CIC gap to every row. CICFlowMeter parity is not claimed.
- [x] R0.3 Record hashes for every selected input and completed output in `r0_real_chunk_files.csv`, the dataset registry and source provenance.
- [x] Audit R0: 15 unlabeled flow CSVs, 1,186,046 rows; zero tuple/time, packet-field, provenance or label-column failures.
- [x] Reviewer pre-authorized R0→R1 once R0's own exit criterion is met and audited; no extra boundary message is required.

## R1 — COMPLETE; audited PASS

- [x] R1.1 Pin the corrected Distrinet rules for the selected dates.
- [x] R1.2 Apply all corrected endpoint, direction, time, port, and expressible payload conditions to R0 flows. Preserve 209 biflow-only attempted-Botnet refinements as explicitly unresolved; broad labels and stages remain verified.
- [x] R1.3 Apply the original CIC schedule independently and retain all 722,627 discrepancies by category and count.
- [x] R1.4 Document matching, timezone, zero time tolerance, overlapping rules, and flow-boundary semantics; hash the methodology.
- [x] Commit the discrepancy log and `REAL_DATA_R1_AUDIT.md`; proceed to pre-authorized R2 after R1 pass.

## R2 — COMPLETE; audited PASS

- [x] R2.1 Build the corpus from all 15 R1 outputs; reconcile 1,186,046 canonical rows.
- [x] R2.2 Strict validation on R1 and canonical data with packet features explicitly required; all counts zero.
- [x] R2.3 Strict preparation with `require_packet_features: true`; 2,558 sequences produced.
- [x] R2.4 Compare real graph endpoint identities, directed edges, bytes, and packets with source flows on all three dates.
- [x] Audit end-to-end results in `REAL_DATA_R2_AUDIT.md`; proceed to pre-authorized R3 after PASS.

## R3 — COMPLETE; audited PASS

- [x] R3.1 Evaluate the preserved epoch-185 checkpoint after exact node, edge, window, history, and normalization contract verification.
- [x] R3.2 Save 41,288 per-window four-step stage, illegal-transition, infiltration, variance, and confidence outputs.
- [x] R3.3 Label all outputs `source: zero-shot, synthetic-trained weights, real-corpus chunk — out-of-distribution test`.
- [x] Audit the restricted Benign/Reconnaissance-only OOD result; manual reviewer sign-off is required before R4.

## R4 — COMPLETE; reviewed real-chunk gate PASS

Manual reviewer authorization was received in-thread on 2026-09-16 with the
instruction `continue`, after delivery of `REAL_DATA_R4_PREFLIGHT.md`. This
authorizes the reviewed `configs/real_chunk_r4.yaml` run only; it does not
authorize R5, R6, main-plan Phase 5, or the GB10 window.

Before starting, flag the proposed overnight run to the user and satisfy
`REAL_DATA_R4_OVERNIGHT_REQUIREMENTS.md`: every-epoch checkpoints, incremental
disk logs, deliberate patience, first-collapse stop, and no automated retries.

- [x] R4.1 Predeclare laptop configuration, split, seed, epoch budget and selection policy.
- [x] Launch the single authorized run; preserve its immediate strict CRF failure and do not retry automatically.
- [x] Audit every target transition: 109 illegal train occurrences (9 unique boundaries), zero validation, and 15 illegal test occurrences (1 unique boundary).
- [x] Establish that seven of ten unique illegal boundaries occur inside active corrected March 1 rule intervals and cannot be justified as externally declared campaign resets.
- [x] Train the combined model on the real chunk only. The authorized second attempt stopped on first validation collapse at epoch 21; no retry occurred.
- [x] R4.2 Evaluate each of four future steps independently: selected epoch 1 passes narrowly with Benign 429 / Initial Access 2, zero illegal transitions, and zero Unknown at every step.
- [x] R4.3 Preserve every attempted epoch checkpoint: all 21 are retained and hashed in the artifact manifest.
- [x] R4.4 Use and justify patience 20 for the 50-epoch, 1,699-sequence run.
- [x] Audit the selected checkpoint, epoch-21 collapse, and unchanged gate outcomes. R5 remains unstarted.
- [x] Include the full no-Lateral-Movement disclosure beside stage coverage and illegal-transition results.

Failure audit: `REAL_DATA_R4_START_FAILURE_AUDIT.md`. The preflight's one real
batch was legal but did not establish whole-corpus CRF target compatibility.
No checkpoint, validation result, R4 pass, or R5 authorization exists.

Reviewer follow-up, 2026-09-20:

- [x] Verify the R0 manifest hash exactly matches the supplied Antigravity hash.
- [x] Declare resets only at the reviewed February 14 FTP/SSH and March 2 Botnet campaign ends in a separate, identity-audited derivative.
- [x] Confirm that the seven March 1 in-campaign boundaries remain untouched and illegal under the unchanged CRF policy.
- [x] Report concrete pipeline impacts for target redefinition, non-monotonic CRF policy, and documented CRF-loss exclusion; implement none pending reviewer choice.
- [x] Trace the earlier 203-passed/13-skipped statement to its execution transcript and disclose that no contemporaneously hashed test artifact exists.
- [x] Receive the reviewer's semantic choice: option (c) authorized; options (a) and (b) rejected.
- [x] Implement exactly seven March 1 CRF structured-loss exclusions while retaining every stage-CE target and leaving Viterbi, the transition policy, and illegal-transition metrics unchanged.
- [x] Audit the option-(c) derivative: 86 modeled repeated edges excluded, five first-target repetitions outside the structured edge model, zero unhandled modeled illegal edges, and zero validation/test exclusions.
- [x] Re-run the complete suite and hash the final result: 206 passed, 13 skipped; the three additional passes are the new option-(c) tests.
- [x] Receive a second explicit reviewer approval before the second R4 training attempt.
- [x] Stop at the first single-stage collapse, epoch 21, without retrying.
- [x] Record the held-out four-step gate and R4 audit in `REAL_DATA_R4_ATTEMPT2_AUDIT.md`.

## R5 — COMPLETE; model loses to feature-matched baseline

- [x] R5.1 Use observed history only, unseen final-window target, threshold fixed at 0.5.
- [x] R5.2 Compare node-only, node+edge, and feature-matched logistic baselines with the world model; include an Always-Benign reference.
- [x] R5.3 Record FPR, confusion counts and explicit single-class fallback status.
- [x] R5.4 Retain hashes, protocol version 3, 431 sample probabilities per model, and limitations.
- [x] State the result plainly: the model loses to the feature-matched baseline on real data.
- [x] Audit in `REAL_DATA_R5_AUDIT.md`; R6 remains unstarted pending review.
- [x] Include the full no-Lateral-Movement disclosure wherever stage coverage or illegal-transition metrics appear.

## R6 — NOT STARTED; reviewer decision required

- [ ] R6.1 Confirm R2 passed.
- [ ] R6.2 Confirm R4/R5 outcomes are recorded.
- [ ] R6.3 Flag a matched-baseline tie to the submission owner if present.
- [ ] R6.4 Record explicit reviewer authorization or hold before any GB10 window.
- [ ] Preserve the full no-Lateral-Movement disclosure in R6 and final submission architecture/novelty sections.

All non-full-corpus metrics use the plan's exact real-chunk source qualifier;
R3 additionally uses its specific OOD qualifier. No result authorizes changing a
fixture, stage definition, tolerance, threshold, or exit gate.

## Independently authorized parallel deliverables

- [x] Isolation root cause and corrected probe: `ISOLATION_ROOT_CAUSE_AUDIT.md`; unchanged predicted risk on the degenerate synthetic graph, no containment-efficacy claim.
- [x] Track E five-slide editable deck: `TRACK_E_SLIDES_AUDIT.md`.
- [x] Track E 80-second captioned MP4: `TRACK_E_VIDEO_AUDIT.md`; captured-state montage, not continuous screen recording. All 1,920 frames decoded; root additionally inspected the actual output table frame and evidence slide.
