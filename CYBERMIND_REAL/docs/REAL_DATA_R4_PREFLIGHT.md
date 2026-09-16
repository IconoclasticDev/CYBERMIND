# Real-data R4 preflight — READY; training not started

Date: 2026-09-16. This document makes the proposed R4 overnight run concrete
for manual review. It is preparation evidence, not authorization. No optimizer
step or model update has run on the R2 corpus.

## Proposed run

Configuration: `configs/real_chunk_r4.yaml`.

| Setting | Frozen proposal |
|---|---|
| Input | R2 real chunk: 1,699 train / 428 validation / 431 held-out test sequences |
| Model | edge features on; CRF stage decoder on; 128 graph/temporal width; 2 temporal layers |
| Window / stride / history | 60 seconds / 30 seconds / 16 states |
| GPU / precision | RTX 5060 Laptop GPU, 7.9 GiB / bf16 |
| Batch | 4, gradient accumulation 4; effective batch 16 |
| Epoch budget | 50 |
| Selection | validation infiltration F1 with 0.05 band, lower validation stage CE tie-break |
| Early-stopping patience | 20 selection events |
| Checkpoint cadence | every epoch, plus selected-best and last |
| Collapse monitor | all 428 validation sequences, four steps, every epoch from epoch 1 |

Patience 20 is chosen for this run rather than copied from the synthetic run.
It doubles the known-too-short default of 10, gives 40% of the 50-epoch budget
for a selection improvement, and still bounds an unattended non-improving run.
The epoch budget and patience are independent of the observed R3 result.

## Durable unattended behavior

The training loop now atomically writes a complete resume payload for every
epoch to `checkpoints/real_chunk_r4/epochs/epoch_NNNN.pt`. Each payload includes
model, optimizer, scaler, epoch, selection state, validation metrics, Python /
NumPy / CPU / CUDA RNG states, class counts, normalization, history, and stale
count. Selected-best and last checkpoints are also atomically replaced.

Metrics append after every epoch to `results/real_chunk_r4/metrics.jsonl` with
flush and filesystem sync. The complete history and status files are atomically
replaced each epoch. Console output will be redirected to durable stdout/stderr
files when the approved run is launched; morning review does not depend on the
process remaining alive.

The validation collapse monitor uses no held-out test samples. At every epoch,
it performs a four-step rollout on all validation histories with four rollouts,
seed 0, and no implicit campaign reset. It declares collapse if any step has
fewer than two distinct non-Unknown decoded stages or is 100% Unknown. At the
first such result the completed epoch checkpoint, metrics, histograms, and stop
status are persisted, then training stops. There is no automatic restart,
retuning, alternate checkpoint substitution, or retry loop. Zero illegal
transitions remains part of the final held-out R4 gate but is not used to hide
or redefine the collapse stop.

This strict policy can stop at epoch 1 if the newly initialized model is already
degenerate. That is the intended consequence of the user's first-sign rule.

## Preflight evidence

The installed CUDA environment reports PyTorch 2.14.0+cu130, CUDA 13.0, PyG
2.8.0.post1, and the RTX 5060. Production dataset/split/provenance checks and
bf16 CUDA matmul passed. The synthetic full-model forward/backward check passed
with all graph, edge-projection, temporal, dynamics, latent, infiltration,
stage, and CRF gradient groups active.

One real batch of four 16-state histories then completed bf16 forward/backward
without an optimizer step. Loss was finite (15.482819), all required gradient
groups were active and finite, peak allocated memory was 78,701,568 bytes, and
peak reserved memory was 79,691,776 bytes. The future-state output head has no
gradient under the existing training loss; that pre-existing behavior is
disclosed and was not counted as an R4 readiness group by the project's earlier
preflight either.

| Evidence | SHA256 |
|---|---|
| Production preflight | `55b60fc0db8cd09d0d77df16490ddb17b9c1be1dcf9aa2a16e585f709f7edf21` |
| Synthetic full-model preflight | `fbe64b10edbd248a47636046e721ed9c6b074db94473544a79011af137aa5d32` |
| Corrected real-batch preflight | `330c3c21e92255d20d039fee512463f4754094227ed3fc8b4552e1dc211ee2b3` |
| Preserved initial diagnostic | `cbc01b2e159a77f8c5f8303e488d9ed2a56319907adfbc3ac4baaa044c5fb126` |

The initial real-batch probe incorrectly required a gradient for every
parameter and therefore marked the unused future-state head as a failure. That
diagnostic is preserved. The corrected probe uses the established required
training gradient groups and passes. No data, model, metric, or exit gate was
changed.

Disk D: has 522,990,485,504 bytes free. Fifty epoch payloads are safely bounded
within that headroom.

## Fixed final R4 evaluation

After training stops or reaches its epoch budget, the selected validation
checkpoint will be evaluated once on the untouched held-out test split. Each of
four steps must have at least two distinct non-Unknown stages, fewer Unknowns
than samples, and zero illegal transitions. The result passes or fails as
observed; no checkpoint substitution or gate change is authorized.

`flow_feature_source: CYBERMIND custom directional packet exporter; 40-column
schema; satisfies the project's 20-field packet-feature contract when verified,
but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter
traffic-statistic columns. No CICFlowMeter feature parity is claimed.`

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.**

## Authorization record

The reviewer authorized this exact reviewed configuration in-thread on
2026-09-16 with the instruction `continue`. R4 may start under the safeguards
above. This authorization does not extend to R5, R6, main-plan Phase 5, or the
GB10 window.
