# CYBERMIND Full Technical Approach

**Problem Statement:** SIH26153  
**Project:** CYBERMIND - Predictive Cyber Defence Platform  
**Primary objective:** Learn the evolution of network state, forecast short-horizon attack risk, compare possible defensive interventions, and validate selected hypotheses in a controlled sandbox.

## 1. Technical Vision

Conventional intrusion-detection systems mainly classify traffic that has already been observed. CYBERMIND instead models the protected network as a sequence of evolving graph states and learns how those states change over time.

The principal technical loop is:

```text
Observe network traffic
    -> construct temporal host-communication graphs
    -> encode the recent network state
    -> forecast multiple future graph windows
    -> estimate future infiltration risk and coarse attack stage
    -> simulate alternative defensive interventions
    -> validate selected attack hypotheses in an isolated Strix Lab
    -> apply and re-test an approved defence
    -> preserve the investigation as a protected incident report
```

The core model answers **what may happen next**. The counterfactual and Strix layers extend this into **what may happen if the defender intervenes, and can that defence withstand a controlled re-test?**

## 2. System Architecture

![CYBERMIND four-tier architecture](../architecture_diagram.jpeg)

CYBERMIND is organized into four technical tiers:

1. **Ingestion, provenance, and flow preparation**
2. **Graph-temporal forecasting model**
3. **Analyst decision support and counterfactual simulation**
4. **Controlled validation, secure reporting, and offline delivery**

All core processing occurs locally. The Windows desktop application and Docker package include the user interface, API, model checkpoint, parsing services, and reporting workflow.

## 3. Input and Telemetry Ingestion

### 3.1 Supported inputs

The analyst manually selects one of the following:

- `.pcap`
- `.pcapng`
- `.cap`
- network-flow `.csv`

No demonstration file is silently preloaded. Each imported case records the source filename and input provenance.

### 3.2 Packet and flow parsing

For packet captures, Scapy-based preparation extracts packet and communication information and aggregates it into flow-like records. For CSV input, the adapter performs fuzzy matching for commonly used fields such as:

- source and destination IP
- source and destination port
- protocol
- timestamp
- flow duration
- packet counts
- byte counts
- optional source label

The parser converts input data into a canonical event schema so the application and model receive a consistent representation regardless of source format.

If a CSV has no timestamps, the application uses a disclosed assumed interval rather than claiming that timing was directly observed. A raw PCAP normally has no verified attack labels; its individual flows therefore remain **Unassessed** unless the source provides valid labels.

### 3.3 Provenance boundary

Every event retains its source identity. This prevents replay data, synthetic lab traffic, uploaded PCAP data, and controlled Strix evidence from being presented as the same kind of observation.

Important evidence categories include:

- `PCAP` or uploaded flow observation
- labeled dataset replay
- synthetic scenario event
- controlled lab probe
- blocked lab probe
- validation record
- analyst-approved defence action

## 4. Temporal Graph Construction

### 4.1 Graph representation

The network is represented as a directed graph:

```text
Node = host, server, endpoint, or device
Edge = observed communication between two nodes
Graph state = communications observed within one time window
Sequence = ordered graph states across time
```

Node and edge features summarize traffic behaviour. Depending on input coverage, these include:

- packet and byte volume
- protocol and port information
- direction
- duration
- packet rate and byte rate
- peer and port diversity
- inter-arrival statistics
- TCP and packet-level statistics
- activity and scanning patterns

### 4.2 Windowing

Canonical events are grouped into overlapping windows:

- **Window size:** 60 seconds
- **Stride:** 30 seconds
- **Maximum retained states:** 64
- **Minimum for forecast:** at least 3 graph windows

The use of overlapping windows provides a continuous view of how the communication graph changes rather than treating every flow independently.

### 4.3 Feature normalization

Training-only means and standard deviations are stored with the selected model configuration. The inference pipeline applies the same normalization and checks that the runtime features are compatible with the checkpoint.

If the checkpoint or its configuration is unavailable or invalid, forecasting is reported unavailable. CYBERMIND does not generate substitute or random scores.

## 5. Graph-Temporal World Model

The bundled checkpoint is `best.pt`, selected from the capture-grouped CIC-IDS2018 experiment.

### 5.1 GATv2 graph encoder

Each host-communication graph is processed using a GATv2 encoder. Attention-based message passing allows the model to learn which nodes and communication relationships contribute most strongly to the graph representation.

```text
Graph G_t -> GATv2 -> graph embedding h_t
```

Edge features are used according to the configuration stored with the checkpoint.

### 5.2 Temporal Transformer

The ordered graph embeddings are passed to a temporal Transformer:

```text
h_(t-H+1), ..., h_t -> temporal Transformer -> latent state z_t
```

The Transformer represents recent network evolution and captures dependencies across multiple observed graph windows.

### 5.3 Latent dynamics model

A learned diagonal-Gaussian transition model estimates how the latent network state may evolve:

```text
P(z_(t+1) | z_t)
```

The transition is applied recursively to produce multiple stochastic future trajectories:

```text
z_t -> z_(t+1) -> z_(t+2) -> ... -> z_(t+K)
```

Multiple rollouts provide a predictive-dispersion signal. This dispersion is treated as an uncertainty proxy, not as a formal calibration certificate.

### 5.4 Prediction heads

The forecast uses multiple heads:

- **Binary infiltration-risk head:** future graph-window risk score
- **Coarse attack-stage head:** distribution over research-stage labels
- **Future-state head:** supports the learned world-model objective
- **Attribution path:** optional gradient-based sensitivity evidence

The application returns:

- current risk
- future-horizon risk
- stepwise risk trajectory
- coarse stage distribution
- model version and checkpoint identity
- inference latency
- predictive-dispersion proxy
- out-of-distribution proxy
- optional feature or graph sensitivity evidence

The risk score applies to an aggregate graph window. It is not a verified probability that a particular host or flow is malicious.

## 6. Flow Triage and Model Forecast Separation

The flow table and the forecasting model perform different functions.

### Flow-triage guard

The application derives Critical, High, Medium, secured, or Unassessed hints from observed flow characteristics and any valid source labels. These categories support investigation and sorting.

### Graph-temporal model

`best.pt` forecasts future risk and stage at the graph-window level. It does not generate the individual flow-table bands.

Keeping these outputs separate avoids presenting rule-based observations as model predictions or presenting unlabeled PCAP traffic as verified malicious activity.

## 7. Analyst Workspace

The React analyst interface communicates with the local FastAPI backend through REST endpoints and WebSocket updates.

### 7.1 Command Centre

The Command Centre combines:

- host and communication graph
- case identity and provenance
- recent events
- current risk context
- model forecast
- timeline navigation
- validation status

Selecting a host or flow connects the high-level graph view to the underlying evidence.

### 7.2 Threat Forecast

The Threat Forecast view presents:

- observed history
- forecast horizons
- graph-window risk trajectory
- coarse stage estimates
- uncertainty indicators
- model metadata

### 7.3 Offline analyst assistant

The bounded assistant uses TF-IDF character n-grams with a scikit-learn intent classifier. It answers read-only questions using the currently loaded case, including flow count, hosts, ports, provenance, labels, and forecast status.

It cannot:

- scan an external system
- modify evidence
- execute a defence
- answer from files that were not loaded
- replace the graph-temporal model

## 8. Parallel Futures and Counterfactual Simulation

Parallel Futures evaluates candidate defensive actions before they are approved.

### 8.1 Simulation method

For every candidate action, CYBERMIND creates a copy of the current graph, applies an allowed in-memory mutation, and reruns the same forecasting model.

```text
Current graph S_t
    -> no-action rollout -> baseline future risk
    -> modified graph S'_t -> intervention future risk
```

Supported intervention concepts include:

- isolate a host
- block a port
- remove or restrict an edge
- rate-limit communication

### 8.2 Recommendation scoring

The defence recommender considers:

- predicted change in future risk
- model confidence proxy
- action reversibility
- collateral-impact heuristic
- available validation evidence

The output is a ranked recommendation for analyst review. Counterfactual results are model-based comparisons and are not claimed as measured causal effects.

## 9. Strix Lab Controlled Adversarial Validation

The Strix Lab is the validation and defence-testing layer of CYBERMIND. It converts the project from a prediction-only system into a closed-loop predictive defence workflow.

```text
Predict -> simulate attack -> observe evidence -> generate defence -> apply -> re-test
```

CYBERMIND contains two related validation paths that must be distinguished.

### 9.1 Built-in offline Attack Lab

The built-in Attack Lab sends bounded, non-destructive HTTP probes to the isolated loopback sandbox at `127.0.0.1:8081`. It never targets an arbitrary external address and never executes shellcode, destructive payloads, or real data exfiltration.

The four implemented attack vectors are:

| Vector | Purpose | MITRE ATT&CK | Weakness |
|---|---|---|---|
| SSH credential brute force | Test whether repeated login attempts are rate-limited or locked out | T1110.001 Password Guessing | CWE-307 |
| SQL injection probe | Test parameter handling with non-destructive Boolean SQL syntax | T1190 Exploit Public-Facing Application | CWE-89 |
| SMB lateral-access probe | Test unauthorized share enumeration and lateral access | T1021.002 SMB Windows Admin Shares | CWE-285 |
| C2 beaconing probe | Test whether egress controls block a simulated HTTP heartbeat to a known test destination | T1071.001 Web Protocols | CWE-200 |

#### Evidence-based verdicts

Every probe is classified from the sandbox's actual response:

- **Succeeded:** the sandbox accepted the vulnerability-specific request
- **Blocked:** an active control returned a rate-limit, WAF, authorization, or structured block response
- **Unreachable:** the target did not respond; no vulnerability verdict is asserted

The Attack Lab records:

- HTTP status
- response body or structured result
- accepted, blocked, and unreachable counts
- generated flow event
- peak and final model risk
- finding identity
- CWE, technique, severity, and affected target

Each real probe outcome is converted into a normalized telemetry event and fed into the state engine. When enough graph states are available, the world model produces an updated risk forecast during the exercise.

### 9.2 AI-assisted remediation and re-test

When the sandbox confirms a vulnerability, the remediation layer can generate a proposed patch or configuration change. The analyst reviews and explicitly applies the defence inside the lab environment.

CYBERMIND then repeats the same probe. The post-defence verdict is based on the new sandbox responses:

```text
Original probe accepted
    -> vulnerability evidence captured
    -> defence generated and approved
    -> same probe executed again
    -> blocked responses verify mitigation
```

This provides direct evidence that the tested mitigation changed the sandbox behaviour. It does not prove that the same patch is safe for every production environment.

### 9.3 Optional external Strix CLI integration

The codebase also includes an adapter for the external Strix CLI. This path is intended for explicitly registered and authorized test targets.

It provides:

- target registration and environment classification
- command construction without arbitrary shell execution
- asynchronous run lifecycle
- timeout and optional budget enforcement
- structured artifact collection
- normalized vulnerability findings
- forecast-to-evidence comparison records

The adapter reads structured artifacts such as:

- `vulnerabilities.json`
- `scan_metadata.json`
- `agent_traces.json`
- `tool_executions.json`

External Strix execution requires:

- Strix CLI
- Docker
- an accessible authorized target
- a configured LLM provider or compatible local model

It is therefore optional and is not part of the guaranteed offline packaged core.

### 9.4 Strix safety gate

Every external Strix run must pass the safety gate:

1. The exact target must be registered.
2. The registration must identify the environment as `SANDBOX`, `REPLAY`, or `AUTHORIZED_TEST`.
3. Unregistered targets are rejected.
4. Autonomous execution is permitted only for the `SANDBOX` class.
5. Timeout and optional cost-budget limits bound the run.
6. Findings are collected from structured artifacts, not scraped from terminal text.

Strix findings are supporting vulnerability evidence. Keyword- or CWE-derived stage hypotheses are always marked inferred and are never treated as verified ATT&CK ground truth.

## 10. Local Validation Engine

The guaranteed offline validation path is separate from the optional external Strix CLI.

After a case has enough graph windows, CYBERMIND:

1. freezes the current forecast
2. calls four bounded endpoints on the bundled in-process sandbox
3. records HTTP status codes
4. hashes response bodies with SHA-256
5. links the record to the forecast ID and model version

The bounded checks cover:

- health response
- invalid login behaviour
- share-access behaviour
- query-handling behaviour

This verifies that the local target responded and preserves tamper-evident response references. It does not independently measure forecast accuracy, establish attack-stage truth, or retrain `best.pt`.

## 11. Protected Incident Reporting

The Reports module creates an incident brief from the current case, model forecast, validation evidence, and intervention context.

### Encryption process

1. Web Crypto generates a random 256-bit AES key.
2. Web Crypto generates a random 96-bit nonce.
3. AES-256-GCM encrypts the incident brief locally.
4. The JSON envelope stores format, version, nonce, and ciphertext.
5. The secret key is shown separately and is not embedded in the encrypted file.

A recipient imports the JSON into CYBERMIND, enters the separately received key, and can view or download the readable report.

AES-GCM provides authenticated encryption: an incorrect key or modified ciphertext fails decryption. The system still requires a trusted method for sharing the separate key.

## 12. Technology Stack

| Layer | Technology | Role |
|---|---|---|
| User interface | React, TypeScript, Vite, Tailwind CSS, React Router, Framer Motion | Analyst command centre and workflow |
| Backend | Python, FastAPI, Pydantic, Uvicorn | Local API, state, forecasts, cases, validation, reporting |
| Live updates | WebSocket | Run, forecast, probe, and validation events |
| Data processing | Scapy, pandas, NumPy, NetworkX | Packet parsing, event normalization, graph construction |
| Machine learning | PyTorch, PyTorch Geometric | GATv2, Transformer, latent dynamics, prediction heads |
| Assistant | scikit-learn | TF-IDF and intent classification |
| Sandbox probes | httpx, FastAPI sandbox | Non-destructive Attack Lab and local validation |
| External validation | Optional Strix CLI adapter | Authorized structured vulnerability validation |
| Report security | Web Crypto, AES-256-GCM | Local authenticated incident-report encryption |
| Windows packaging | PyInstaller, PySide6, Qt WebEngine | Native desktop runtime |
| Container packaging | Docker Compose, prebuilt Linux x86-64 images | Offline container deployment |

## 13. Deployment Architecture

### Windows desktop

The complete Windows folder contains:

- `CYBERMIND.exe`
- bundled React assets
- FastAPI backend
- Python and native dependencies
- `best.pt`
- local sandbox components
- demonstration data

The executable starts a FastAPI service on an ephemeral `127.0.0.1` port and opens the application in a native Qt WebEngine window. No browser tab, separate Python installation, CUDA runtime, or cloud endpoint is required for the core application.

### Docker

The Docker package contains:

- prebuilt Linux x86-64 image archives
- Docker Compose configuration
- SHA-256 manifest
- Windows and Linux launch scripts
- named-volume persistence

The application binds to `127.0.0.1:8000`. The launch process loads the bundled images locally rather than pulling them at runtime.

## 14. Evaluation Approach

The selected checkpoint was evaluated using a capture-grouped CIC-IDS2018 protocol:

- four observed graph windows
- four future graph windows
- capture groups separated across training, validation, and test
- no random distribution of rows from one episode across all splits
- threshold fixed at 0.5 for the saved comparison

### Held-out pooled binary results

| Metric | CYBERMIND `best.pt` | Feature-matched logistic baseline |
|---|---:|---:|
| F1 | 0.984854 | 0.926632 |
| Precision | 0.997008 | 0.931416 |
| Recall | 0.972993 | 0.921898 |
| False-positive rate | 0.005650 | 0.131356 |

These results support binary short-horizon graph-window forecasting on the documented split. They do not establish universal performance on every organization, network, or attack family.

The recorded stage macro-F1 is substantially lower than the binary risk score. Coarse stage predictions must therefore be presented as research estimates rather than authoritative ATT&CK-stage truth.

## 15. Failure Handling

CYBERMIND follows explicit failure behaviour:

- invalid or missing model -> forecasting unavailable
- insufficient graph windows -> forecast deferred
- unsupported input -> validation error with no fabricated output
- unreachable sandbox -> no attack verdict asserted
- blocked probe -> recorded as blocked, not successful
- Strix unavailable -> core forecasting remains operational
- external Strix timeout or failure -> comparison remains inconclusive
- incorrect report key or modified ciphertext -> decryption fails

## 16. Security and Operational Boundaries

The following boundaries are fundamental to the technical approach:

1. Raw PCAP traffic is not automatically given attack ground-truth labels.
2. Flow-table risk bands are not `best.pt` predictions.
3. The model forecasts graph windows rather than identifying a verified malicious person or device.
4. Rollout variance is an uncertainty proxy, not a calibrated confidence certificate.
5. Parallel Futures is a model simulation, not proof of causal effect.
6. Strix Lab probes are bounded and non-destructive.
7. External targets require explicit authorization and registration.
8. Strix findings support the investigation but do not establish model-stage accuracy.
9. Sandbox activity does not continuously retrain `best.pt`.
10. Production deployment would require security review, broader external validation, threshold calibration, operational key exchange, and reviewed model-update procedures.

## 17. Complete Operational Workflow

```text
1. Analyst imports PCAP or flow CSV
2. Backend records provenance and creates canonical flow events
3. Events form overlapping host-communication graph windows
4. best.pt forecasts future graph-window risk and coarse stage
5. Analyst inspects topology, flows, timeline, and explanations
6. Parallel Futures compares no-action and modified graph rollouts
7. Defence recommender ranks reversible candidate interventions
8. Analyst optionally runs a controlled Strix Lab probe
9. Sandbox responses establish whether the tested vector was accepted or blocked
10. Probe telemetry updates the case and model risk view
11. Confirmed vulnerability produces a proposed remediation
12. Analyst approves the lab defence
13. The same probe is repeated to verify the mitigation
14. Forecast, evidence, decisions, and validation results enter the incident brief
15. The report is encrypted locally with AES-256-GCM
16. Recipient imports and decrypts it inside CYBERMIND using the separate key
```

## 18. Technical Differentiation

CYBERMIND does not stop at static intrusion classification. Its differentiation is the integration of:

- graph-based network-state representation
- temporal multi-step forecasting
- stochastic future trajectories
- explicit uncertainty and provenance
- counterfactual defence simulation
- controlled Strix attack validation
- AI-assisted mitigation with re-probe verification
- offline analyst workflow
- authenticated encrypted incident reporting

The resulting closed loop is:

```text
OBSERVE -> FORECAST -> SIMULATE -> VALIDATE -> DEFEND -> RE-TEST -> REPORT
```

This makes the platform useful not only for identifying current risk, but also for exploring what may happen next, comparing possible responses, and collecting evidence that a selected defence changes the behaviour of a controlled target.
