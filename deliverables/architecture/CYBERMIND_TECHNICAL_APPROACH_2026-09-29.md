# CYBERMIND — Predictive Cyber Defence Platform

**Diagram subtitle:** Offline network-traffic analysis, graph-based attack forecasting, analyst decision support, and protected incident reporting.

## Diagram layout

Use one landscape architecture diagram with **five grouped areas**, like the supplied reference image. Use the labels below as the text inside the boxes. Show the main data path with solid arrows. Keep labels short enough to remain legible.

```text
┌──────────────────────────┐     ┌──────────────────────────┐     ┌────────────────────────────┐
│ 1. ANALYST INPUT         │────▶│ 2. LOCAL APPLICATION     │────▶│ 3. FORECASTING ENGINE     │
│                          │     │ FastAPI + REST/WebSocket │     │                            │
│ • PCAP / PCAPNG upload   │     │                          │     │ 1. Flow → temporal graphs  │
│ • CICFlowMeter CSV upload│     │ • Parse network flows    │     │ 2. GATv2 graph encoder    │
│ • Manual case selection  │     │ • Normalize features     │     │ 3. Temporal Transformer   │
└──────────────────────────┘     │ • Maintain case state    │     │ 4. Latent dynamics rollout│
                                 └────────────┬─────────────┘     │ 5. Risk + stage heads      │
                                              │                   └─────────────┬──────────────┘
                                              ▼                                 │
                                 ┌──────────────────────────┐                   │
                                 │ 4. LOCAL DATA LAYER      │◀──────────────────┘
                                 │ • Telemetry + graph state│
                                 │ • Pinned best.pt model   │
                                 │ • Forecast/case records  │
                                 └────────────┬─────────────┘
                                              │
                                              ▼
                                 ┌──────────────────────────────────────────────────────────┐
                                 │ 5. ANALYST WORKSPACE (REACT UI)                          │
                                 │ • Network graph + timeline  • Multi-step threat forecast │
                                 │ • Flow risk triage          • Parallel-futures comparison │
                                 │ • Local sandbox validation • Read-only NLP assistant     │
                                 │ • Incident brief → AES-256-GCM export → in-app decryption│
                                 └──────────────────────────────────────────────────────────┘
```

## Exact arrows and labels

| From | Arrow label | To |
|---|---|---|
| PCAP / CSV upload | Captured packets or flow records | FastAPI ingestion |
| FastAPI ingestion | Canonical, source-tagged flow events | Telemetry and temporal graph builder |
| Temporal graph builder | Ordered host/communication graph windows | `best.pt` forecasting model |
| `best.pt` forecasting model | Future risk trajectory, coarse attack stage, uncertainty | Threat Forecast and Command Centre |
| Telemetry buffer | Observed flows and source labels | Flow risk triage table |
| Current graph state | Baseline and simulated interventions | Parallel Futures |
| Current case + forecast | Read-only facts | NLP assistant |
| Frozen forecast | Bounded HTTP checks and response hashes | Local sandbox validation record |
| Forecast + case evidence | Incident brief | Local AES-256-GCM encryption |
| Encrypted JSON + separately shared key | Import, decrypt and view | Reports section in CYBERMIND |

## Box annotations

- **Model:** bundled, pinned `best.pt`; PyTorch inference on CPU or CUDA when available. It forecasts **graph windows**, not individual-flow classes.
- **Flow risk triage:** Critical/High/Medium/secured indicators are **rule-based hints from observed features and any source labels**, separate from model forecasts. Unlabeled raw PCAP flows remain **Unassessed**.
- **Parallel Futures:** runs the same model on the current graph and on in-memory, modified graph copies; outputs are simulated comparisons for analyst review.
- **Local validation:** checks the bundled sandbox target and records actual HTTP responses next to a frozen forecast. It does not retrain `best.pt`.
- **NLP assistant:** offline TF-IDF + scikit-learn intent classifier; answers bounded, read-only questions about the loaded case.
- **Report security:** a fresh random 256-bit key encrypts each incident brief with AES-256-GCM. The encrypted JSON excludes the key; the recipient imports the JSON and enters the key in CYBERMIND's Reports section to decrypt and view or download a readable copy.
- **Deployment footer:** **Windows:** native `CYBERMIND.exe` with bundled UI/backend/model. **Linux x86-64:** offline Docker app. Report encryption and decryption are available inside the application; all core processing stays local.
