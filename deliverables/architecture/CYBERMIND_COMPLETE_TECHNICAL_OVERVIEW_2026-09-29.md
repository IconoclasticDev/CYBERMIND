# CYBERMIND — Complete Technical Overview

**Release described:** `CYBERMIND_ALL_IN_ONE_2026-09-29`  
**Purpose:** Offline network-traffic investigation and short-horizon attack-risk forecasting with an analyst-facing desktop/Docker application.  
**Selected checkpoint:** `best.pt`, SHA-256 `5324902ca017e946af58b41fbd576561553d7c03b532b37ee9255f4a3677cf39` (validation-selected epoch 21 from the capture-grouped CIC-IDS2018 experiment).

## 1. Solution at a glance

CYBERMIND accepts a packet capture or network-flow CSV, converts it to a common event schema, builds a time-ordered series of host-communication graphs, and uses a graph-temporal PyTorch model to forecast the risk and coarse attack stage of future graph windows. An analyst can inspect the network graph, observed flows, model forecast, simulated defensive alternatives, local validation responses, and a case report. The report can be encrypted, imported, decrypted, viewed, and saved as readable JSON **within the CYBERMIND Reports section**.

The key distinction is between **observations**, **model forecasts**, and **analyst aids**. A PCAP supplies observed packets and derived flows, but normally no ground-truth attack labels. The model predicts at the **graph-window level**. The table's Critical/High/Medium/secured flow flags are **rule-based triage hints derived from observed features and supplied source labels**, not per-flow classifications by `best.pt`.

```text
Manual PCAP/CSV import
  → FastAPI parser + provenance
  → canonical network-flow events
  → rolling time windows and host-communication graphs
  → pinned best.pt graph-temporal model
  → multi-step risk/stage forecast + uncertainty proxy
  → React analyst views and in-memory defence simulations
  → case/validation records
  → AES-256-GCM incident brief export
  → in-app JSON decryption and readable download
```

## 2. Tech stack

| Layer | Technology in this release | Role |
|---|---|---|
| Analyst interface | React 19, TypeScript 5.9, Vite 7, Tailwind CSS 4, React Router 7, Framer Motion, Lucide icons | Offline, responsive command centre, investigation, forecast, reports, and interaction. |
| API and live updates | Python, FastAPI, Pydantic, Uvicorn, REST, WebSocket | Local upload, state/forecast queries, case records, validation endpoints, and push updates. |
| PCAP/flow preparation | Scapy, pandas, NumPy, NetworkX, project graph-builder code | Packet-to-flow extraction, CSV column matching, event normalization, temporal graph construction. |
| Trained model | PyTorch, PyTorch Geometric; GATv2 graph encoder, temporal Transformer, learned latent dynamics, risk/stage heads | Multi-step graph-window forecasting using the bundled `best.pt` checkpoint. |
| Analyst NLP | scikit-learn TF-IDF character n-grams + logistic-regression intent classifier | Local read-only questions over the loaded session; deterministic, bounded responses. |
| Local validation | httpx ASGI transport, bundled FastAPI sandbox target, SHA-256 hashing | Records four actual local target responses beside a frozen forecast. |
| Report protection | Web Crypto API, AES-256-GCM, cryptographically random 256-bit report key and 96-bit nonce | Client-side encrypted JSON export and in-app authenticated decryption. |
| Windows desktop | PyInstaller folder build, PySide6 / Qt WebEngine | Native `CYBERMIND.exe` window with bundled React assets, backend, dependencies, and model. |
| Container deployment | Docker Compose, prebuilt Linux/amd64 images, Python 3.11 slim app image, Node 24 frontend build stage | Offline image loading and Linux x86-64/Windows Docker operation. |
| Local persistence | JSON run/validation records, filesystem directories; Docker named volume | Retains experiments and validation evidence locally. |

The Windows executable runs its own FastAPI service on an ephemeral `127.0.0.1` port and displays the React UI inside Qt WebEngine. It is a native window, though its frontend and backend communicate over local HTTP. The Docker variant serves the same UI from FastAPI on `127.0.0.1:8000`. Neither core runtime requires a CDN or an online model endpoint.

## 3. Input formats and provenance

The analyst manually selects a `.pcap`, `.pcapng`, `.cap`, or `.csv` file. A PCAP is parsed locally into network-flow records; a CSV uses fuzzy matching for columns such as source/destination IP, ports, protocol, timestamps, duration, packets, bytes, and optional attack label. Events carry source provenance identifying the uploaded file. The CSV upload route currently processes up to 2,000 rows; if timestamps are absent, the application applies **disclosed assumed one-minute spacing**, rather than claiming to have observed timing.

The event stream is transformed into overlapping graph windows (60-second window, 30-second stride; at most 64 retained states). Hosts become nodes and communications become edges with numeric traffic features. At least three graph windows are required for a forecast. This graph builder is shared with the model's data pipeline, reducing mismatch between training features and application inference.

**Raw-PCAP boundary:** ordinary packet captures do not include verified benign/attack labels. The flow table therefore marks unlabeled PCAP flows `UNASSESSED`/unknown. The application can still form graph windows and produce a model forecast; that forecast must not be presented as a verified per-flow attack label. Labeled CIC-IDS2018 CSV examples can show the flow-triage categories because their labels come with the source data.

## 4. Model architecture and inference

1. **Graph encoder:** GATv2 embeds each host-communication graph, optionally using edge features according to the checkpoint configuration.
2. **Temporal encoder:** a Transformer processes the ordered graph embeddings into a latent representation of the observed network state.
3. **Dynamics model:** learned latent transitions generate multiple stochastic future trajectories.
4. **Prediction heads:** infiltration-risk and coarse attack-stage heads produce future-window scores and stage distributions; a future-state head supports the world-model formulation.
5. **Application formatter:** returns current and horizon risk, stepwise trajectory, stage hints, model identity, a confidence proxy, an out-of-distribution proxy, and latency. Explanations use model-gradient attribution where requested.

The backend loads `best.pt` once per process, checks its configuration and weights, applies saved training-time feature normalization, and chooses CPU when CUDA is unavailable. If the checkpoint is missing or invalid, inference is reported unavailable rather than inventing scores. The **bundled Docker app is explicitly CPU-based**. The selected checkpoint uses **argmax stage decoding**, not a CRF decoder.

Risk and confidence require careful interpretation: the risk is a **model score for an aggregate graph window**, not a verified probability that a named flow or host is malicious. Stochastic rollout variance represents predictive dispersion; the UI confidence and OOD indicators are proxies, not calibration certificates. Coarse stage/technique mappings help an analyst navigate the evidence but do not establish ground truth from an unlabeled capture.

## 5. Analyst workflow and features

| Feature | What it uses | What it returns |
|---|---|---|
| Command Centre / network view | Observed graph snapshot, flow events, latest forecast | Interactive host/edge view, timeline, risk and stage context. |
| Threat Forecast | Recent graph states and `best.pt` | Current and future-window risk/stage trajectory with model metadata. |
| Flagged-Flows table | Recent flow records and any supplied labels | Rule-based risk bands, source/stage hints, sortable investigation rows. Unlabeled PCAP rows remain unassessed. |
| Parallel Futures | Current graph state, proposed actions | Baseline model rollout compared with rollouts on in-memory modified graphs (for example host isolation, port blocking, rate limiting). |
| Defence recommendations | Simulated risk change, confidence, reversibility, collateral-impact heuristics, available validation evidence | Ranked suggestions requiring analyst approval for consequential actions. It does not itself enforce controls on a production network. |
| Scenario/replay and experiments | Synthetic/replayed events and case state | Reproducible demonstrations and local records with source provenance. |
| Floating NLP assistant | Loaded events, labels, hosts, ports, provenance, forecast and model status | Bounded natural-language answers. It cannot run a scan, modify data, or answer from unloaded files. |
| Reports | Current case, forecast, model and intervention context | Encrypted incident brief; in-app import/decrypt/view; readable JSON download after decryption. |

Counterfactual results are **model-based simulations**, not measured causal effects. They compare what the same model predicts after a permitted in-memory graph modification; they do not prove a real firewall rule would have the shown impact.

## 6. Validation engine

After a case has enough graph windows to generate a forecast, the **built-in local check** freezes that forecast, calls four bounded endpoints on a bundled in-process sandbox target (health, invalid login, share access, and query handling), and stores HTTP status codes plus SHA-256 hashes of the response bodies. The record links the observed responses to the forecast ID and model version. This verifies that a local target responded; it **does not** independently label an attack stage, measure model forecast accuracy, or retrain the model.

The code also has a separate controlled-Strix integration for registered, authorized sandbox targets. That path needs the Strix CLI, a live target, and a configured LLM provider; it is **not part of the guaranteed offline core** and may be unavailable in the packaged runtime. Docker socket access alone does not supply those prerequisites. CYBERMIND does **not** continuously update `best.pt` from sandbox activity. Any future learning loop would need reviewed labels, drift monitoring, offline evaluation, and a new approved checkpoint.

## 7. Encrypted incident reports

The current export creates a fresh, random **256-bit AES key** and **96-bit nonce** using Web Crypto. AES-256-GCM encrypts the incident brief locally before the JSON file is saved. The downloaded envelope stores the format/version, nonce, and ciphertext, **not the secret key**. The 43-character base64url report key is shown separately and can be copied. A recipient imports the encrypted JSON in CYBERMIND's **Reports** section, enters the separately received key, and can inspect or download the resulting readable JSON. The application also understands a legacy PBKDF2-HMAC-SHA-256 passphrase-based format for older reports.

AES-GCM authenticates the ciphertext: an incorrect key or modified file fails decryption. This is **symmetric encryption**, not LWE or public-key encryption. The sender still needs a trusted way to share the report key with the intended recipient. Possession of both file and key permits decryption; a downloaded readable copy is unencrypted.

The **normal workflow is entirely in-app**. The current Docker bundle also contains a redundant standalone decrypter image for compatibility, but it is not needed to decrypt a report in CYBERMIND.

## 8. Offline packaging and operation

**Windows desktop:** the complete `Windows` folder contains `CYBERMIND.exe`, `_internal` with the UI/backend/model/native dependencies, and demo data. Double-clicking the EXE opens a native Qt window. It does not require Docker, a separate Python installation, CUDA, or a browser tab. The first startup can take longer while the CPU model loads. Application data and logs are stored under `%LOCALAPPDATA%\CYBERMIND`.

**Docker:** the bundle contains prebuilt Linux/amd64 image archives, SHA-256 manifest, Compose file, and Windows/Linux launch scripts. The scripts verify the image archives and load them locally without pulling at runtime. Docker Engine and Compose must already be running. The app binds to `127.0.0.1:8000`; data uses a Docker named volume. The Compose file mounts the host Docker socket for its controlled-validation integration—this grants the container substantial control of the host Docker daemon. The Linux/amd64 image was tested under Docker Desktop; native Linux host behavior and ARM64/macOS builds have not been independently verified.

The bundle includes manually selectable CIC-IDS2018 SSH brute-force and Botnet Ares CSV examples plus real PCAP examples and provenance notes. The CSVs are suitable for demonstrating labeled flow risk triage; a raw PCAP is suitable for demonstrating packet ingestion and graph-window forecasting. No demo file is preloaded.

## 9. Evaluation evidence and limits

The selected checkpoint was evaluated in a **capture-grouped CIC-IDS2018 held-out four-observed-window → four-future-window protocol**. The saved test predictions were independently recomputed against a feature-matched logistic baseline; this verification uses saved outputs, **not a fresh inference run inside the UI**. At the fixed 0.5 binary decision threshold:

| Pooled held-out test metric | CYBERMIND `best.pt` | Feature-matched logistic baseline |
|---|---:|---:|
| Binary infiltration F1 | 0.984854 | 0.926632 |
| False-positive rate | 0.005650 | 0.131356 |
| Precision | 0.997008 | 0.931416 |
| Recall | 0.972993 | 0.921898 |

These figures support binary future-window infiltration forecasting **on that specific split**. They do not establish performance on a different network or all public cybersecurity datasets. The same saved evaluation reports **stage macro-F1 of 0.244304**; the checkpoint does not reliably forecast every kill-chain stage. The flow table's rule-based bands and the sandbox's successful HTTP responses are **not** additional model-accuracy measurements.

## 10. What the solution delivers

The refined prototype is a locally runnable analyst tool that connects raw/labeled network input, graph-temporal risk forecasting, visual investigation, bounded natural-language querying, simulated defence comparison, local sandbox response evidence, and protected case sharing. The strongest defensible technical claim is **short-horizon binary graph-window forecasting on the evaluated CIC-IDS2018 protocol**, presented with transparent provenance and limitations. A production deployment would still require broader external validation, security review, operational key exchange, calibrated alert thresholds, and controlled model updates.

For a compact visual, use the separate `CYBERMIND_ARCHITECTURE_2026-09-29.svg` diagram and `CYBERMIND_TECHNICAL_APPROACH_2026-09-29.md` diagram brief.
