# CYBERMIND Windows desktop app

Open the complete `CYBERMIND` folder and double-click `CYBERMIND.exe` inside it. Keep the EXE and `_internal` together in that one folder. The app opens in its own native window. Windows does not need Docker, Python, or a browser to run this build.

Keep the EXE and its `_internal` directory together. `_internal` contains the UI, native runtime, and pinned `best.pt` model. The model SHA-256 is `5324902ca017e946af58b41fbd576561553d7c03b532b37ee9255f4a3677cf39`. The first launch may take longer while the model loads on CPU.

The React UI and bundled FastAPI backend communicate over an ephemeral, private `127.0.0.1` connection inside the app. There is no browser tab, fixed port, LAN listener, Docker dependency, or network download at runtime. Closing the app window stops its backend. User-generated runs and logs are stored under `%LOCALAPPDATA%\CYBERMIND`.

The separate Linux x86-64 Docker bundle uses the same UI and model. Its `launch_linux.sh` verifies and loads the image archives, then starts the app with Docker Compose. The built-in local sandbox check generates a fresh forecast for a loaded case and records four actual target responses. The Windows app discovers Docker Desktop's per-user or system CLI when installed and running. Optional Strix controlled validation still requires the Strix CLI, a live registered sandbox target, and an LLM provider; Docker access alone does not supply those prerequisites.
