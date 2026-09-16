# Real-data R0 toolchain and stage-coverage review

Reviewed 2026-09-16 against `C:/Users/as030/Downloads/CYBERMIND_Real_Data_Validation_Plan.md`. This is a read-only scout apart from this report. No dataset was selected, downloaded, regenerated or relabeled; no R1–R6 work or training was started. **R0 exit criteria are not met.**

## Installed tools and existing exporters

PowerShell `Get-Command` and CPU-venv `shutil.which` find no `java`, `javac`, `tshark`, `nprobe`, `cicflowmeter`, `gradle` or `mvn` on PATH. `JAVA_HOME` is absent. No matching Java/JDK/Adoptium/Wireshark/ntop directories were found in the standard Program Files locations. This is bounded discovery, not proof that no private installation exists anywhere on disk.

The `.phase01-venv` Python import probes find **Scapy**, but not `dpkt`, `cicflowmeter` or `pyshark`. Repository searches find no CICFlowMeter/nProbe exporter wrapper, packaged JAR, or named flowmeter executable. `requirements.txt` provides Scapy for optional PCAP ingestion, not either requested exporter.

| Existing path | What it actually does | R0 mismatch |
|---|---|---|
| `scripts/pcap_to_corpus.py` | Runs custom Scapy extraction recursively; infers labels from filenames | Not CICFlowMeter/nProbe; labels before R1; catches errors and prints SKIP |
| `src/cybermind/data/pcap_extract.py` | IPv4 directional sessions, inactivity timeout, packet statistics | Not bidirectional CIC flows; not the requested ~80 feature schema |
| `scripts/regenerate_join_day.py` | Calls a hardcoded February 14 victim-capture regeneration | Not a 2–3-day unlabeled exporter |
| `src/cybermind/data/cic_day.py` | Bounded-memory classic Ethernet PCAP processing, minute buckets, schedule-based labels | Hardcoded original Feb14 schedule; labels participate in flow grouping; skips non-IPv4/fragmented traffic |

AST inspection counts exactly **40 `_row` output columns** in `pcap_extract.py`: seven endpoint/time columns, nine basic flow measurements, four label/stage columns, and twenty packet-feature fields (including availability). Backward bytes, packets and IAT are fixed at zero because these are directional records. This is useful existing infrastructure, but cannot be relabeled as a CICFlowMeter-compatible ~80-feature export.

The official tool is a Java biflow exporter; the documented output retains endpoints and more than 80 statistics. Flow direction, termination and timeout semantics matter, so matching a few column names is insufficient. [CIC dataset and extraction documentation](https://www.unb.ca/cic/datasets/ids-2018.html)

The upstream implementation documents native jnetpcap dependencies plus Maven/Gradle build paths. A pinned exporter version, native/runtime setup and a small schema smoke check are needed before processing days. The existing toolchain does not justify silently choosing nProbe or a similarly named Python package. [CICFlowMeter upstream](https://github.com/ahlashkari/CICFlowMeter)

Packet features required here additionally include TTL moments, fragmentation ratios, raw TCP-window moments, payload quantiles, scan-order statistics and retransmissions. CIC flow export alone does not demonstrate these exact project fields. An explicit augmentation must associate packets with the exporter's actual bidirectional flow boundaries, preserve first/last packet timestamps and directional payload totals, and record inclusion/exclusion counts. Joining custom minute buckets or 300-second directional sessions by five-tuple alone would be ambiguous for reused connections.

## Do published schedules establish the required stages?

CIC Table 2 lists infiltration on February 28/March 1 and bot traffic on March 2. Its narrative describes internal scanning and backdoor activity, but Table 2 supplies attack categories rather than separately verified Reconnaissance, Lateral Movement and C2/Exfiltration stage labels. [CIC schedule](https://www.unb.ca/cic/datasets/ids-2018.html)

Distrinet splits infiltration into Dropbox download, NMAP portscan and victim-attacker communication. It documents scan-report transfer on February 28 and bot messages/uploads on March 2. This supports investigating reconnaissance and communication/upload behavior, **not automatically assigning verified lateral movement**. Its corrected rules also use ports and payload conditions: an endpoint/time-only join loses distinctions. Heartleech lacks supporting capture evidence; SQL correction concerns mislabeled subsets, not absence of all SQL attacks. The published page contains a January/February date inconsistency beside Unix timestamp 1519829140; preserve and resolve that discrepancy explicitly before coding rules. [Distrinet corrected documentation](https://intrusion-detection.distrinet-research.be/CNS2022/CSECICIDS2018.html)

The linked labeling implementation is an additional primary artifact to pin and cross-check against the documentation before R1. [Distrinet labeling repository](https://github.com/GintsEngelen/CNS2022_Code)

**Inference:** choosing two infiltration days and one bot day would not by itself prove the exact R0.1 three-stage requirement. Internal port scanning is not evidence of successful movement to another host. Mapping a broad infiltration label to Lateral Movement would fabricate the missing evidence. No day combination is selected by this review.

## Blockers and required next decisions

1. **Stage-coverage blocker:** obtain evidence for actual lateral-movement traffic with defensible labeling, or obtain an explicit reviewer revision of R0.1. Do not silently substitute reconnaissance for lateral movement or claim stage coverage from filenames.
2. **Exporter gap:** no requested exporter is currently callable. Establish a pinned supported runtime/exporter and verify five-tuples, timestamps and the full feature schema before bulk execution.
3. **Packet-augmentation gap:** define exact packet-to-biflow membership and feature semantics; existing custom exporters cannot satisfy this by renaming their outputs.
4. **Label-contract discrepancy:** preserve the R0 output unlabeled; R1 needs the complete corrected rules, including ports, directional payload tests, time conventions and overlap precedence. The plan's endpoint/time shorthand is not the full published predicate set.

The archive-size assertion, full archive availability and source/output hashes are not revalidated by this toolchain scout. R0 completion requires real selected-day flow files and registered hashes; this report supplies none and claims no pass.
