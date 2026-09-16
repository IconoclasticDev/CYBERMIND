# Real-data R4 start failure audit — exit criterion NOT MET

Date: 2026-09-16. The single reviewer-authorized R4 run was launched with
`configs/real_chunk_r4.yaml` and stopped during its third training batch, before
epoch 1 completed. There was no automated retry.

## Concrete outcome

The process raised:

```text
ValueError: illegal target transition at timestep 4; declare an explicit reset if appropriate
```

The exception originated in `StageDecoder.forward()` while scoring the CRF
target path. No epoch checkpoint, metric record, validation evaluation, or
collapse-monitor result was produced. The run status is
`failed_before_epoch_1`; `last_completed_epoch` and completed optimizer steps
are both zero. The stdout and stderr SHA256 values are respectively
`9ac5cb91874855b6062f728ba6d8ecae11bc8c8ada5ae5e92ca7cab740fbe204`
and `e702a80d30045e54273b8a7092e60f06fa2ea6242cdbccd22643333b841c77ed`.

## Whole-corpus target audit

`scripts/audit_r4_target_transitions.py` evaluates every adjacent target under
the unchanged matrix in `knowledge/stage_mapping.yaml`. Overlapping 16-state
histories repeat the same physical boundary, so both occurrence and unique
boundary counts are reported.

| Split | Adjacent occurrences | Illegal occurrences | Unique illegal boundaries | Pairs |
|---|---:|---:|---:|---|
| train | 25,485 | 109 | 9 | Initial Access→Benign: 34/4; Reconnaissance→Benign: 75/5 |
| validation | 6,420 | 0 | 0 | none |
| test | 6,465 | 15 | 1 | Command & Control→Benign: 15/1 |

The first number in each pair entry is the repeated occurrence count and the
second is the unique temporal-boundary count. All 40,928 inspected state
occurrences have no declared `campaign_reset` metadata.

Three unique transitions align with independently published corrected-rule
ends and could be declared from external time metadata: February 14 FTP at
16:10:31 UTC, February 14 SSH at 19:32:30 UTC, and March 2 Botnet at 19:54:52
UTC. Their affected destination windows begin after those ends.

The other seven unique transitions do not align with a campaign boundary. Two
Initial Access→Benign reversions occur at 13:53:42 and 13:57:42 UTC inside the
active March 1 Dropbox interval (13:53:10–13:59:20). Five
Reconnaissance→Benign reversions occur inside the continuous corrected NMAP
interval (14:09:48.354333–19:38:12.182726). They are 30-second occupancy
dropouts inside active external rules. Declaring resets there from the target
reversions would violate the decoder contract that emissions and target labels
never imply a reset.

The stored `attack_label` is modal among flow rows, whereas `y_stage` records
whether any attack-stage flow is present. It can therefore read `BENIGN` in a
mixed window whose target stage is non-Benign; it is not evidence for a reset.

## Root cause and preflight gap

The graph target is a per-window attack-flow-presence category. Sparse attack
flows can disappear between adjacent overlapping windows while an externally
defined campaign interval remains active. The CRF target policy represents a
monotonic kill-chain trajectory unless an external reset is declared. Those
two semantics are incompatible for seven observed boundaries.

The reviewed CUDA preflight evaluated one legal batch. It proved memory,
forward/backward, and gradient viability for that batch but did not scan every
target path. The new audit closes that coverage gap and fails before an
expensive run.

No reset was invented, no transition matrix or exit gate was changed, no
offending history was dropped, and no alternate checkpoint was substituted.
Resolving this requires a reviewed choice of target representation or an
externally defined episode/reset policy. Marking every attack→Benign reversion
as a reset is specifically unsupported by the available external evidence.

## Verdict

**R4 exit criterion NOT MET.** Training did not complete one epoch, no
real-trained checkpoint exists, and the fixed four-step gate cannot be run.
R5 is not authorized and has not started.

`flow_feature_source: CYBERMIND custom directional packet exporter; 40-column
schema; satisfies the project's 20-field packet-feature contract when verified,
but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter
traffic-statistic columns. No CICFlowMeter feature parity is claimed.`

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.**
