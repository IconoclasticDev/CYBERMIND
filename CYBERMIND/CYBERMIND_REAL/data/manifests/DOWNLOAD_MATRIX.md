# Public data collection matrix

| Source | Can script download? | Why | CYBERMIND role |
|---|---|---|---|
| CSE-CIC-IDS2018 | Yes (AWS S3) | Public AWS bucket | Primary training |
| CIC-IDS2017 | Web form/manual | UNB download workflow | Cross-dataset validation |
| UNSW-NB15 | Web form/manual | Official UNSW research download | Cross-dataset validation |
| CTU-13 | Web/manual | Stratosphere dataset portal | C2/botnet validation |
| CICIoT2023 | Web/manual | CIC/cicresearch download | IoT/topology validation |
| LANL Authentication | Web/manual | Research data portal | Auxiliary identity/time context |
| DARPA 1998/1999 | Web/manual | MIT Lincoln Laboratory pages | Historical sequence validation |
| MITRE ATT&CK | Yes (HTTP) | Public STIX repository | Attack ontology |
| CAPEC | Yes (HTTP) | Public MITRE download | Attack-pattern ontology |
| NVD | Yes (API) | Public NVD 2.0 API | Vulnerability context |
| NCIIPC | Manual/public review only | Government/organizational resource; do not scrape protected material | India/CII context + contact |

## Important

The repository does not vendor multi-GB/100-GB research datasets. `scripts/download_public_sources.py` automates the sources that are directly retrievable; the remaining official portals are documented in `configs/sources.yaml` and `docs/PUBLIC_DATA_SOURCES.md`.
