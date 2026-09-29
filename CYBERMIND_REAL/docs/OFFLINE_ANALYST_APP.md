# Legacy Streamlit workflow (replaced by FastAPI/React)

The primary app and packaging instructions are in [FASTAPI_REACT_APP.md](FASTAPI_REACT_APP.md). This document describes the retained Streamlit implementation.

# Offline analyst application workflow

The trained checkpoint is loaded locally. The application does not call a cloud API.

## Launch

Install `requirements.txt` and the matching PyTorch Geometric runtime, then run:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m streamlit run scripts\app.py --server.address 127.0.0.1
```

On Linux or macOS, use that platform's Python environment and run
`python -m streamlit run scripts/app.py --server.address 127.0.0.1`.
The project virtual environment used for the trained checkpoint includes
PyTorch Geometric; a generic PyTorch-only runtime may not load its graph weights.

The first launch creates one local analyst password of at least 12 characters.
The account hash is stored at `~/.cybermind/account.json` by default. Set
`CYBERMIND_HOME` to choose a persistent directory for a packaged application.
The account file contains a password hash, not a decryption key. Keep the
password: there is no recovery key for encrypted case files.

## Analyze and replay

Upload a PCAP, PCAPNG, or packet-complete CSV. The selected checkpoint requires
packet-feature coverage and rejects flow-only CSVs. Capture rows are always
treated as unlabeled during inference. The replay slider selects one observed
history at a time; forecasts at earlier positions use only traffic available by
that window. The replay chart records the final-horizon risk at positions the
analyst has visited. It does not silently run inference over the entire capture.

The flow table lists up to 200 rows from the selected observed window. Its
review flags are transparent indicators for port-access patterns or TCP
retransmissions. They are not learned per-flow attack predictions. The model
provides network-level future risk. Stage 3–5 evidence rules and abstention are
shown separately from the raw model stage.

The case-question box answers common questions about future risk, displayed
stages, observed flow cues, host-set changes, and file hashes. It is deterministic
evidence search, not a general-purpose language model. Answers cite fields in
the current case and do not infer a cause or a verified future event.

The input feature-range check counts training-normalized node and edge values
beyond six training standard deviations. It is an uncalibrated caution cue,
not an OOD detector or a reliability estimate.

## Encrypted reports

In **Case lineage and encrypted export**, confirm the local password and create
a `.cmcase` file. The case is serialized to JSON, encrypted with AES-256-GCM,
and protected by a fresh Argon2id-derived key and random salt for each export.
The app does not offer a plaintext report download in this workflow.
Two encrypted cases can also be opened together for a side-by-side comparison
of their saved risk, reported stage, flagged-flow count, replay position, and
input hash. The comparison does not re-score either case.

Use **Open encrypted report** to import the file. The app verifies the local
login password again before decrypting it, and AES-GCM rejects tampering or an
incorrect password. This is an offline, single-analyst workflow. The password
must be strong because an attacker holding a case file could attempt offline
guesses. The local account is not a multi-user enterprise identity system.

## Evidence boundary and packaging

The final grouped checkpoint is suitable for the demonstrated four-window
binary attack-risk forecast on its grouped CIC-IDS2018 evaluation. Its stage
head did not correctly identify unseen Command & Control targets in the held-out
test; stage labels in the UI are annotations for analyst review, not a claim of
validated full kill-chain prediction. Capture replay and encrypted export do not
change the checkpoint or its evaluation.

The current `sandbox/docker-compose.yml` is an isolated placeholder, not an
application container. No Windows executable or Linux/macOS container image has
been built or verified by this workflow. A distributable package must include
the appropriate PyTorch Geometric runtime, checkpoint, offline dependencies,
local-only binding, and persistent `CYBERMIND_HOME` storage, then be tested on
each target platform.


