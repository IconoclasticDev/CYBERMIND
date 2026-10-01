# CYBERMIND

**Offline network investigation and graph-based attack forecasting for SIH26153.**

CYBERMIND ingests a PCAP/PCAPNG capture or CICFlowMeter CSV, preserves its provenance, builds temporal host-communication graphs, and runs the pinned `best.pt` model to forecast future graph-window risk and coarse attack stage. The analyst desktop also provides observed-flow triage, counterfactual comparisons, a local sandbox check, case-grounded questions, and encrypted incident briefs.

![CYBERMIND architecture](deliverables/architecture/architecture_diagram.jpeg)

## Start here

| I want to… | Open |
|---|---|
| Run the current offline desktop release | [Docker desktop bundle](releases/CYBERMIND_DOCKER_DESKTOP_DEMO_READY_2026-09-30.zip) · [setup and platform notes](releases/README.md) |
| Inspect the application and model source | [CYBERMIND_REAL](CYBERMIND_REAL/) · [source guide](CYBERMIND_REAL/README.md) |
| Read the technical approach | [Full technical approach](deliverables/SIH26153_CYBERMIND_FULL_TECHNICAL_APPROACH.md) · [architecture document](deliverables/architecture/CYBERMIND%20Architecture%20Document.html) |
| Review the demonstration | [Demo video](deliverables/demo/CYBERMIND_demo.mp4) · [narration script](deliverables/demo/script.md) |

The current release is the **2026-09-30 Docker desktop bundle**. Extract it to a short path and keep its files together. On Windows, start `CYBERMIND.exe` with Docker Desktop's Linux engine running. On Linux x86-64, run `sh launch_linux.sh` with Docker Engine and the Compose plugin. The bundle contains its Docker image and pinned model, so startup does not pull them from the network. The app opens in its desktop window on Windows; the local loopback connection is internal to the desktop/Docker setup. [Release details and limitations](releases/README.md).

## Repository map

```text
CYBERMIND_REAL/   Product source: React UI, FastAPI, model, tests and Docker build
deliverables/     Architecture, technical documents, script and demo video
releases/         Versioned runnable bundles and integrity manifests
tools/            Document builders and optional pinned Strix archive
README.md         This entry point
```

Generated environments, extracted bundles, raw captures, render intermediates, and large local datasets are kept out of Git. They are not needed to navigate the source repository. The [older SIH submission package](releases/CYBERMIND_SIH_PACKAGE_README.md) is retained for provenance; use the current Docker desktop bundle to run the app.

## What the demo actually shows

- **Model forecast:** `best.pt` predicts future *graph windows*. It does not assign ground-truth classes to individual raw PCAP flows.
- **Observed flow flags:** Critical, High, Medium and Secured are rule-based triage hints from observed features or supplied source labels. Unlabeled flows can remain Unassessed.
- **Parallel Futures:** compared branches are simulations from the same model, not applied changes to live traffic.
- **Validation:** the built-in local check records bounded sandbox HTTP responses and hashes beside a frozen forecast. Optional Strix-controlled scans require a configured CLI, sandbox target and provider; they are not active in the bundled release.
- **Reports:** the app encrypts incident briefs with AES-256-GCM and decrypts them within the Reports view using a separately held key.

For training, evaluations, setup details and tests, see the [source guide](CYBERMIND_REAL/README.md) and [implementation status](CYBERMIND_REAL/IMPLEMENTATION_STATUS.md).

Built by Team Untangle.
