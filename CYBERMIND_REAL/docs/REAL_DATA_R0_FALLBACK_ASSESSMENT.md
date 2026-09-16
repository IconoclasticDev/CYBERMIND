# R0 custom-exporter fallback assessment

Date: 2026-09-16. **Fallback is technically viable for the project's strict
packet-feature gate, but it does not satisfy the original approximately
80-feature CICFlowMeter target.** This is a declared coverage gap, not feature
parity. No selected-day fallback export has been run yet.

## R2 packet-feature gate

`scripts/validate_dataset.py --strict --require-packet-features` requires the
20 names in `PACKET_FEATURES`: 19 finite packet-derived measurements plus
`packet_features_available == 1`. `scripts/prepare_data.py --strict` enforces
the same finite/all-available contract when `require_packet_features: true`.

The custom PCAP extractor emits all 20 required fields from packet observations:
TTL mean/variance, TCP-window mean/variance, IP DF/MF/fragment ratios, payload
mean/variance/min/max/quartiles, scan-port/order scores, and retransmission
count/ratio, plus the availability flag. It also emits endpoint identities,
ports, protocol, start/end times and nine basic flow statistics. Focused tests
completed **6 passed, 0 skipped**, including an explicit strict validator pass
with packet features. Therefore, after corrected R1 labels and verified complete
input processing, its rows can satisfy the current R2 packet-feature check.

That conclusion is about the implemented validator contract. It does not prove
full capture coverage, correct R1 labels, a faithful CIC biflow, or R2 end-to-end
success. Those gates must still be run on completed selected-date outputs.

## Feature-coverage gap

The pinned CICFlowMeter source declares **84 CSV columns**: seven identity/time
columns, 76 traffic-statistic columns, and one label. The custom exporter emits
**40 columns**: seven endpoint/time columns, nine basic flow statistics, four
label/stage fields, and 20 packet-feature fields.

Only nine basic custom flow fields directly cover the pinned flow-statistic
families: duration, forward/backward packet totals, forward/backward byte totals,
flow bytes/s, flow packets/s, and forward/backward IAT mean. Relative to the 76
pinned traffic-statistic columns, **approximately 67 CICFlowMeter statistics are
absent**. Missing families include most direction-specific length distributions,
IAT total/std/min/max, TCP flag counts, header lengths, direction rates,
down/up ratio, bulk, subflow, initial-window, active and idle statistics.

The custom packet fields add project-required telemetry that the pinned schema
does not express identically, but they do not erase the missing CIC feature
families. Column counts are not a semantic equivalence test. The fallback also
uses directional sessions rather than CICFlowMeter biflows; reverse-direction
statistics are currently zero in each row. This is a material topology/feature
semantics difference.

## Required fallback work before R0 can pass

1. Freeze exact capture membership for March 1 and March 2; retain the reviewed
   February 14 derivative and unchanged source hashes.
2. Separate unlabeled R0 export from schedule labeling. R0 output must not use
   the current hardcoded February 14 schedule or group flows by label.
3. Make flow semantics explicit and deterministic. If directional sessions are
   retained, record that choice and do not call them CICFlowMeter-compatible
   biflows. Preserve inclusion/exclusion counts for non-IPv4 and fragments.
4. Publish only atomically completed outputs; retain failures and partial files
   under unmistakable names.
5. Record source/output hashes and this feature-gap statement in the registry
   and provenance before requesting R1 approval.
6. Run R1 corrected labels, then the unchanged R2 strict validator and strict
   preparation. Do not weaken either gate because the fallback has fewer flow
   features.

## Mandatory provenance label

Use this text with every fallback dataset and derivative:

> `flow_feature_source: CYBERMIND custom directional packet exporter; 40-column
> schema; satisfies the project's 20-field packet-feature contract when verified,
> but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter
> traffic-statistic columns. No CICFlowMeter feature parity is claimed.`

R0 exit criteria are amended only to the extent of the reviewer's approved
fallback instruction. The R2 packet requirement, stage disclosure, downstream
rollout gate and benchmark protocol remain unchanged.

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.** Real-data evaluation is pending.

