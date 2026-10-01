# R0 Reviewer Decision Log — 2026-09-16

Authority: the user's explicit reviewer decision in this conversation. The
Downloads plan was inspected after that message; its local copy did not yet
contain the named decision-log section. This record preserves the decision
without overwriting the previously hashed plan snapshot.

## Approved scope

Selected dates are frozen: **February 14 / March 1 / March 2, 2018**.
Mandatory Lateral Movement coverage in R0.1 is removed by reviewer approval.
All other gates remain unchanged. No date may be swapped to obtain a pass.

The reviewer imposed this non-negotiable condition:

> every downstream artifact that reports stage coverage or the illegal-transition-rate metric — R4, R5, R6, and the final submission's architecture/novelty sections — must state explicitly that real-chunk validation does not include a Lateral Movement transition, and that kill-chain-diversity is validated on real data for the other stages only.

Required disclosure in each applicable artifact (not merely a link elsewhere):

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.**

Until an evaluation passes, report validation as pending or failed, not as a
successful validation of the remaining stages. A zero illegal-transition rate
does not establish correctness of transitions involving Lateral Movement.
Include this disclosure in R3 outputs too when they report the affected metrics.

## Approved malformed-source derivative

Create a distinct derivative containing all **4,718,327 complete records** of
the existing February 14 victim capture. Preserve and hash the source unchanged.
Exclude the final record at byte offset **852,795,085**: 291 payload bytes are
available out of 371 declared. Exclusion is 307 on-disk bytes including its
16-byte record header. No byte synthesis or record repair is authorized.
Retain the original extraction and validation failures as evidence.

## Authorization boundary

R0 only is authorized. R1 and every later phase remain unauthorized.
Before CICFlowMeter runtime pinning/schema verification, provide a bounded
estimate and check it against the remaining timeline. No open-ended setup work.
See `REAL_DATA_R0_RUNTIME_ESTIMATE.md` for the proposed time box.
