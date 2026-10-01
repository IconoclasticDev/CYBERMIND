# CYBERMIND

**Predictive cyber defence for Smart India Hackathon problem statement SIH26153.**

CYBERMIND turns PCAP/PCAPNG captures or flow CSVs into time-ordered host graphs. Its pinned `best.pt` graph-temporal model forecasts future graph-window risk and a coarse attack stage. The offline analyst application combines those forecasts with observed-flow triage, counterfactual defence comparisons, local sandbox evidence, a case-grounded assistant, and encrypted incident reporting.

![Four-tier CYBERMIND architecture](CYBERMIND/deliverables/architecture/architecture_diagram.jpeg)

## Judge's quick access

| Item | Open |
|---|---|
| Complete project files | [CYBERMIND folder](CYBERMIND/) |
| Architecture document | [Architecture document](CYBERMIND%20Architecture%20Document.html) |
| Current offline application | [Windows and Linux Docker bundle](CYBERMIND/releases/CYBERMIND_DOCKER_DESKTOP_DEMO_READY_2026-09-30.zip) · [run instructions](CYBERMIND/releases/README.md) |
| Technical approach | [Full technical approach](CYBERMIND/deliverables/SIH26153_CYBERMIND_FULL_TECHNICAL_APPROACH.md) |
| Demonstration | [Video](CYBERMIND/deliverables/demo/CYBERMIND_demo.mp4) · [script](CYBERMIND/deliverables/demo/script.md) |

The release ZIP contains the offline Docker image, pinned model, Windows `CYBERMIND.exe` launcher, Linux x86-64 launcher, and manual demo inputs. Keep the extracted bundle together. Windows needs Docker Desktop's Linux engine; Linux needs Docker Engine and the Compose plugin. See the [run instructions](CYBERMIND/releases/README.md) for the exact setup and platform limits.

The model forecasts **graph windows**, not individual-flow labels. Flow risk flags are separate rule-based hints. Parallel Futures shows model simulations, while the built-in Validation Engine records local sandbox responses beside a frozen forecast; optional Strix scans need additional configuration. Incident briefs use AES-256-GCM and can be decrypted inside the app with a separately held key.

For source code, tests, documents, releases, and optional tools, open the [project folder](CYBERMIND/). The architecture PDF is currently a **review preview**; its final filename will be chosen after approval.

Built by Team Untangle.
