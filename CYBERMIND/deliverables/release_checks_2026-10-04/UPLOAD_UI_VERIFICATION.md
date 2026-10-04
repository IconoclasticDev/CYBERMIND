# Shared desktop / Docker UI verification — 4 October 2026

Release: `CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04`.

- TypeScript and Vite production build passed.
- The Windows EXE and Linux launcher use the same Compose file, which mounts the bundled `ui/` directory read-only at `/app/frontend/dist`. Backend and pinned model remain in the verified offline image; no second image rebuild/export was performed.
- Docker Compose started the updated release without pulling or building. Inspection confirmed the shared UI mount and existing persistent data volume.
- The new release's Windows EXE opened a `CYBERMIND — Analyst Console` window. Its launcher log confirmed connection to the same updated Docker service at `127.0.0.1:58425`.
- Running UI verified at its assigned loopback port: model online on CPU, WebSocket connected, no initial uploaded data. Scenario Lab, sidebar test cases/active scenario, sample-loading controls and Recent Events card are absent.
- System Health is absent from Command Centre and appears within Settings below Neural Engine Status. Its live backend, model, pipeline, window and WebSocket values remain intact. Screenshot: `settings-system-health.jpg`.
- Validation panel displays persisted real sandbox results with timestamps, frozen forecast stage, response status and expandable full response hashes. External Strix remains a separate collapsed, unconfigured capability; no LLM or autonomous Strix execution is claimed.
- Local validation now polls for updates every five seconds while idle. Attack Lab displays actual accepted/blocked/unreachable response counts and recovered session patches.
- A pre-existing, unreferenced legacy `MitreTechniqueModal.tsx` imports absent legacy data. It is excluded from the TypeScript project; the application does not import this component.

The base image's full-machine offline checks are documented in `RELEASE_VERIFICATION.md`. The physical-network-off test was not repeated for this UI-only update. Linux execution still requires verification on a Linux x86-64 host; this check used Windows Docker Desktop. All release launchers require Docker installed and running. Keep `ui/`, Compose, image archive and EXE together.
