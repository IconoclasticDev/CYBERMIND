# CYBERMIND — Public Data & Knowledge Sources

## Primary network training source

### CSE-CIC-IDS2018
Official AWS open-data mirror: https://registry.opendata.aws/cse-cic-ids2018/

The registry describes seven attack scenarios (Brute-force, Heartbleed, Botnet, DoS, DDoS, Web attacks, infiltration), network traffic/log resources, 80 traffic features, and the public S3 bucket `s3://cse-cic-ids2018/` accessible with `--no-sign-request`.

**CYBERMIND use:** primary training corpus; prefer endpoint-aware flow/PCAP material so the temporal graph has real host identities.

## Cross-dataset validation

### CIC-IDS2017
Official: https://www.unb.ca/cic/datasets/ids-2017.html

Provides labeled flows and PCAPs, endpoint IP/port/protocol information, attack timing/scenarios, and 80+ traffic features via CICFlowMeter.

**Use:** cross-dataset generalization + unseen scenario/family tests.

### UNSW-NB15
Official: https://research.unsw.edu.au/projects/unsw-nb15-dataset

The official page describes PCAP/BRO/Argus/CSV resources, 9 attack categories, 49 commonly used features, and an academic research usage grant with citation requirements.

**Use:** robustness validation; keep source-specific provenance.

### CTU-13
Official: https://www.stratosphereips.org/datasets

The Stratosphere Laboratory describes CTU-13 as 13 botnet scenarios with manually labeled botnet, command-and-control, normal, and background traffic.

**Use:** C2/botnet trajectory validation.

### CICIoT2023
Official: https://www.unb.ca/cic/datasets/iotdataset-2023.html

The official CIC page describes 33 attacks across 7 categories in a 105-device IoT topology and provides PCAP and CSV directories.

**Use:** topology-heavy and IoT transfer validation, not mandatory for first CIC-IDS2018 training run.

### LANL Authentication Dataset
Official portal: https://csr.lanl.gov/data/

**Use:** auxiliary temporal identity edges (user↔computer authentication). This is a different event family from packet/flow telemetry and is therefore modeled as auxiliary context rather than silently merged into flow labels.

### DARPA IDS datasets
1998: https://www.ll.mit.edu/r-d/datasets/1998-darpa-intrusion-detection-evaluation-dataset
1999: https://www.ll.mit.edu/r-d/datasets/1999-darpa-intrusion-detection-evaluation-dataset

MIT Lincoln Laboratory provides sample/training/testing network and audit data and associated truth/documentation.

**Use:** historical sequence robustness; preserve dataset family as an independent domain.

## Knowledge bases

### MITRE ATT&CK
Official data tools: https://attack.mitre.org/resources/attack-data-and-tools/
STIX repository: https://github.com/mitre-attack/attack-stix-data

Use a dated Enterprise ATT&CK STIX 2.1 snapshot for reproducibility. ATT&CK is the ontology/reference layer, not a substitute for attack-stage ground truth in the network datasets.

### CAPEC
Official downloads: https://capec.mitre.org/data/downloads

The current public page reports CAPEC version 3.9 with 559 attack patterns and provides ZIP/XML/CSV representations.

### CVE / NVD
Official: https://nvd.nist.gov/
API 2.0: https://services.nvd.nist.gov/rest/json/cves/2.0

Use versioned API/range snapshots only for vulnerability context. Never depend on live NVD requests in offline inference.

## India / CII context

### NCIIPC
Government directory: https://www.india.gov.in/category/science-it-communication/subcategory/research-development/details/website-of-national-critical-information-infrastructure-protection-centre
Website: https://www.nciipc.gov.in/

The Government of India directory identifies NCIIPC as the national nodal agency for Critical Information Infrastructure Protection. The SIH problem text supplied to the team also lists `helpdesk1@nciipc.gov.in` as the contact pathway.

**Rule:** only ingest explicitly public/open material. Do not request or include operational network telemetry, protected CII details, credentials, or classified/sensitive information.

## Provenance rule

Every normalized record retains:

`source`, `source_file`, `scenario_id`, timestamp method, endpoint-identity method, label/stage mapping method.

This prevents accidental cross-dataset label leakage and lets the final report state exactly which source produced each result.
