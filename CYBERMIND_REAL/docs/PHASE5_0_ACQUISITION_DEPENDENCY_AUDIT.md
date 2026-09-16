# Phase 5.0 acquisition dependency audit — pre-GB10 finding

Date: 2026-09-16. Read-only review performed in parallel with R0 fallback.
No Phase 5/GB10 run was started.

## Verdict

The corpus-acquisition commands **do not depend on CICFlowMeter, jnetpcap, Java,
or nProbe**. The CICFlowMeter NO-GO is therefore not a direct failure of the S3
download step. However, the current production path has a more immediate
GB10-scale blocker: it contains **no archive extraction, packet-to-ground-truth
join, or packet-feature enrichment stage** between downloading the bucket and
building the corpus. With the production config, that path will deterministically
fail strict preparation on flow-only CSVs.

## Actual call path

1. `scripts/prepare_cic2018_public.sh:5-13` creates the raw directory, runs an
   unsigned `aws s3 sync`, and writes a sorted file listing. It does not unpack
   PCAP ZIP/RAR archives or call a flow exporter.
2. `scripts/download_public_sources.py:35-41` is an alternate unsigned S3 sync
   and records only source/method/URI provenance. Its `zipfile` import is unused.
3. `scripts/launch_training.py:55` invokes the shell downloader; lines 58-64
   then call `build_corpus.py` directly.
4. `scripts/build_corpus.py:37-46` recursively discovers **CSV only**. It does
   not read PCAP, ZIP or RAR files.
5. `UnifiedAdapter` at `src/cybermind/data/adapters/unified.py:89-90` copies the
   20 packet fields if they already exist; otherwise it fills them with zero.
   Importing `PACKET_FEATURES` supplies names, not extraction.
6. `scripts/launch_training.py:120` calls the validator without
   `--require-packet-features`, then line 122 calls strict preparation.
7. `configs/gb10_full.yaml:11` requires packet features. The check at
   `scripts/prepare_data.py:94-104` rejects rows unless every packet field is
   finite and `packet_features_available == 1`. Flow-only inputs therefore fail.

The optional `scripts/pcap_to_corpus.py` is not called by the production path.
It uses the custom Scapy extractor rather than CICFlowMeter, accepts only already
extracted capture files, converts extraction errors to `SKIP`, and assigns
filename-derived labels or `PCAP_EVENT`. It does not implement the verified
CIC-IDS2018 label join required for production training.

## Consequence before GB10

Phase 5.0 can download 477.32 GB, but the current launcher cannot turn that
download into training-ready packet-enriched rows. The R0–R2 fallback work must
be generalized into an explicit production archive extraction, atomic custom
flow export, corrected labeling and strict validation stage before opening the
GB10 window. Simply changing the exporter name would not fix the missing call
path. The fallback's approximately 67 missing CIC traffic statistics and
directional-session semantics must remain disclosed at GB10 scale.

No automatic full-corpus fallback integration is authorized by this audit. It
must be reviewed after the real-chunk R0–R3 evidence and before Phase 5 execution.

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.** This audit reports pipeline
dependencies, not successful real-data validation.
