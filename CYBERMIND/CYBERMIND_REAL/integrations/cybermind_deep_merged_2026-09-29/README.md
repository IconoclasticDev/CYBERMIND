# CYBERMIND application source

This is the current application build context. Packaged offline users should
start `CYBERMIND/START_WINDOWS.cmd` or `sh CYBERMIND/START_LINUX.sh` from the
repository root. Those launchers prepare the complete Windows/Linux release,
including its saved Docker image; they do not require a Python or Node setup.

## Working files

- `app/`: API, ingestion, forecasting, analyst support and sandbox validation.
- `src/`: graph-temporal inference and supporting model code.
- `frontend/`: React UI source and locked frontend dependencies.
- `models/best.pt`: the checkpoint copied from the verified deployed application.
- `results/final_grouped_model_comparison.json`: saved model benchmark evidence.
- `knowledge/`, `data/test_cases/`, `examples/test_cases/`: required build inputs;
  supplied samples are manually selected, not automatically loaded.
- `sandbox/`: bundled local validation target.
- `packaging/`: desktop launcher sources, PyInstaller specifications and container entrypoint.
- `Dockerfile`, `compose*.yaml`: container build and optional Strix Docker access.

## Build from source

With Docker and Compose installed, run `docker compose up --build -d` here.
The initial source build downloads base images and dependencies. For offline
operation without a source build, use the saved image in the packaged release.
The backend defaults to CPU; CUDA is not required. Decryption is inside the app.
External autonomous Strix requires a separately configured CLI and LLM provider.

Historical training runs, copied web consoles, design references, caches and
notebooks are not part of this tracked application build context.
