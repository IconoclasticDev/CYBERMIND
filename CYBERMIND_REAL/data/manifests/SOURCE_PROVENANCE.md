# CYBERMIND source provenance

The SIH problem statement names public sources including CIC-IDS2017/2018, UNSW-NB15, CTU-13, CICIoT2023, LANL Authentication, DARPA intrusion-detection datasets, and public knowledge bases including MITRE ATT&CK, CAPEC and CVE/NVD.

Official/current landing pages used by the acquisition manifest:

- CIC-IDS2017: https://www.unb.ca/cic/datasets/ids-2017.html
- CICIoT2023: https://www.unb.ca/cic/datasets/iotdataset-2023.html
- UNSW-NB15: https://research.unsw.edu.au/projects/unsw-nb15-dataset
- CTU-13: https://www.stratosphereips.org/datasets-ctu13
- LANL Cyber1: https://csr.lanl.gov/data/cyber1/
- DARPA 1998: https://www.ll.mit.edu/r-d/datasets/1998-darpa-intrusion-detection-evaluation-dataset
- DARPA 1999: https://www.ll.mit.edu/r-d/datasets/1999-darpa-intrusion-detection-evaluation-dataset
- MITRE ATT&CK STIX: https://github.com/mitre-attack/attack-stix-data
- CAPEC downloads: https://capec.mitre.org/data/downloads.html
- NVD: https://nvd.nist.gov/
- NCIIPC: https://www.nciipc.gov.in/

Raw datasets are intentionally not copied into this code archive. Their sizes, download mechanisms and licenses vary. The acquisition helpers preserve source URL/method/provenance in `data/manifests/`.

## Local real-data precheck — failed, preserved (2026-09-16)

The raw-data exclusion above is a distribution policy. A local February 14,
2018 victim-host capture has since been acquired into the ignored raw directory;
this does not mean the full corpus was downloaded or included in the code archive.

- Source: CSE-CIC-IDS2018 S3, `Original Network Traffic and Log data/Wednesday-14-02-2018/pcap.zip`, member `pcap/UCAP172.31.69.25`.
- Local path: `data/raw/CIC-IDS-2018/one_day_2018-02-14/UCAP172.31.69.25.pcap`.
- Size: 852,795,392 bytes. SHA256: `008f18cce0ff420ce013eba6d97ae0b974f36028a0707a977f78d4bfd7f48afc`.
- Archive CRC32 `c2144ce9` verified; the exact source member itself has a truncated final record. No repair has been applied.
- Scope: one victim-host capture, not the whole day's host population.
- Earlier partial directional output: `data/one_day_join/events.parquet`, SHA256 `ef2c2b6fb0ea78c09fd1ab3b3a9c0279f0b61ad6f5c92a8290e37073f6474f45`; **failed extraction and strict validation**, not a completed R0 flow CSV.
- Evidence: `examples/one_day_join/`, `examples/real_data_validation/r0/preserved_input_hashes.json`, `docs/REAL_DATA_R0_AUDIT.md`.

No R0 completed flow-output hash exists yet. No row in the registry certifies
this source as training-ready. Every new completed export requires its own hash
and exact capture/flow-boundary provenance before R0 can pass.

## Reviewer-approved February 14 derivative — 2026-09-16

- Authorization: `docs/REAL_DATA_R0_REVIEWER_DECISION_2026_09_16.md`; R0 only.
- Derivative: `data/raw/CIC-IDS-2018/one_day_2018-02-14/UCAP172.31.69.25.complete_records.reviewed_2026-09-16.pcap`.
- SHA256: `7fc8442ebf996dc065bbbad3cfb6a9bcde247b58cb8e459fca144a1bbf607394`; 852,795,085 bytes; 4,718,327 complete packet records.
- Source: the unchanged victim capture above, SHA256 `008f18cce0ff420ce013eba6d97ae0b974f36028a0707a977f78d4bfd7f48afc`, reverified after derivation.
- Excluded record: offset 852,795,085; 291 of 371 declared payload bytes available; 307 bytes excluded including the 16-byte record header. No synthesized bytes or repaired record.
- Verification: complete-record boundary/count scan; derivative SHA256 equals the source-prefix SHA256; original hash unchanged. `examples/real_data_validation/r0/feb14_derivative.json` records the evidence and excluded-tail hash.
- Scope remains one victim-host capture with the final incomplete record excluded, not the entire date's host population. Original failed runs are retained. No flow export or labeling is implied.

Frozen dates: February 14 / March 1 / March 2, 2018. **Real-chunk validation does
not include a Lateral Movement transition. Kill-chain-diversity validation on
real data covers the other represented stages only; it does not validate Lateral
Movement.** Real-data evaluation is still pending. This disclosure must remain
in every applicable downstream artifact, including the final submission.

## R0 exporter decision — CICFlowMeter no-go; custom fallback (2026-09-16)

The final bounded CICFlowMeter attempt installed verified Temurin Java 8 but the
pinned build failed because `org.jnetpcap:jnetpcap:1.4.1` was unavailable from
all declared repositories. Per reviewer instruction, no manual artifact install,
debugging, alternate release or third attempt was made. See
`docs/REAL_DATA_R0_CICFLOWMETER_FINAL_ATTEMPT.md`.

The approved fallback is the CYBERMIND custom directional packet exporter. Its
40-column schema includes all 20 fields enforced by the project's strict packet
feature check, but it is not feature-equivalent to the pinned 84-column
CICFlowMeter schema. It has nine basic flow statistics versus 76 pinned traffic
statistics, leaving approximately 67 CIC traffic-statistic columns absent.
Direction/session semantics also differ. Exact gap and required work:
`docs/REAL_DATA_R0_FALLBACK_ASSESSMENT.md`.

Required label on future fallback outputs: `flow_feature_source: CYBERMIND custom
directional packet exporter; 40-column schema; satisfies the project's 20-field
packet-feature contract when verified, but is not CICFlowMeter and omits
approximately 67 of the pinned CICFlowMeter traffic-statistic columns. No
CICFlowMeter feature parity is claimed.` No fallback selected-day output exists
yet, so no output hash or R0 pass is claimed.
