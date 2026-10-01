# FastAPI + React offline analyst app

The primary app now uses a React frontend served by FastAPI. It accepts unlabeled PCAP, PCAPNG, or supported packet-complete CSV files, replays observed histories, forecasts four future windows, displays evidence and flows, simulates host-isolation sensitivity, and encrypts case reports. The prior Streamlit entry point remains in the repository as a legacy implementation. The start screen also offers two reproducible synthetic PCAP files (web-like and sequential-port traffic) alongside local upload. Their manifest records SHA-256 hashes; they are walkthrough inputs, not validation data or evidence of model accuracy.

## Run locally on Windows

From this project directory:

    .venv\Scripts\python.exe -m pip install -r requirements.txt
    cd web
    npm ci
    npm run build
    cd ..
    .venv\Scripts\python.exe scripts\launch_desktop.py

The launcher binds to 127.0.0.1 and opens a browser. The local account lives in the user's .cybermind directory. Uploaded captures exist as temporary files only during parsing and are deleted afterwards. Case sessions stay in memory.

When an encrypted `.cmcase` is opened with the local password, the app automatically downloads a self-contained, print-ready HTML report and shows the decrypted case in the Case file view. The HTML can be opened offline and printed or saved as PDF. It is **unencrypted plaintext** and should be handled as sensitive evidence. The original `.cmcase` remains encrypted. The Case file view also has a button to download the readable report again.

## Windows executable

Build React first, install PyInstaller into the project virtual environment, then run scripts\build_windows_exe.ps1. Distribute the entire dist\CYBERMIND folder, including its model and web assets. The application is large because the graph model and PyTorch runtime are bundled. A Windows build must be verified on the target Windows architecture.

## Docker

Run docker compose -f compose.app.yaml build followed by docker compose -f compose.app.yaml up, then open http://127.0.0.1:8000. The image contains the model and frontend assets, so runtime inference needs no internet. Docker itself must be installed; its Linux image is separate from the Windows executable.

## Trust and limitations

The API loads only the trusted local checkpoint configured by CYBERMIND_CHECKPOINT, never a model uploaded over HTTP. The selected grouped checkpoint has a narrow real-data binary result; an earlier three-day chunk's separation was almost entirely explained by the engineered scan_sequential_score feature. The model did not generalize to held-out C2 stage. Stage annotations from telemetry rules are shown separately and are not claimed as trained stage accuracy. The input-range cue is heuristic and host-isolation simulation is model sensitivity, not measured containment effectiveness. Encrypted case files use Argon2id and AES-256-GCM.

