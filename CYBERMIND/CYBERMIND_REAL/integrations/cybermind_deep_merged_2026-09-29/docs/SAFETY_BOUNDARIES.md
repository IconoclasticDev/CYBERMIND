# Safety Boundaries

CYBERMIND is a **defensive research platform**. These boundaries are enforced
in code, not by convention.

## Hard invariants

1. **Registration required.** No Strix execution without a prior
   `POST /api/strix/targets` registration of the exact target string.
   `TARGET_NOT_REGISTERED` (HTTP 403) otherwise.
2. **Explicit environment classification.** Only `SANDBOX`, `REPLAY`,
   `AUTHORIZED_TEST` are accepted. `PRODUCTION`-like values are refused at
   registration (`INVALID_ENVIRONMENT`).
3. **Autonomous mode is sandbox-only.** `authorize_autonomous()` rejects any
   non-SANDBOX environment (`AUTONOMOUS_NOT_SANDBOX`).
4. **Forbidden target classes.** `AUTHORIZED_TEST` registrations may not
   address loopback (`127.0.0.0/8`, `::1`), link-local (`169.254/16`,
   `fe80::/10`) — this blocks cloud-metadata-style endpoints
   (`FORBIDDEN_TARGET`). SANDBOX/REPLAY explicitly cover loopback lab rigs.
5. **No arbitrary commands.** The HTTP API never accepts shell commands.
   Interventions are a fixed enum (`Isolate Host`, `Block Port`, …). The only
   subprocess ever spawned is the Strix binary with argv built by
   `StrixClient.build_command()` from validated fields (targets/instructions
   are checked for control characters; argv is passed as a list, never through
   a shell).
6. **Secrets never logged.** `LLM_API_KEY` is passed through the child process
   environment only. It never appears in argv, logs, or stored records.
7. **No silent live-looking synthetic data.** Replay/demo data is labeled
   `REPLAY` / `SYNTHETIC`; controlled scans are `CONTROLLED LAB` evidence.
8. **Single subprocess path.** All Strix runs flow through `StrixRunner`,
   which enforces a hard timeout, kills on stop, and runs the child with CWD
   pinned to the managed runs directory.

## Input validation

- Target strings: ≤512 chars, no CR/LF/NUL (client + schema level).
- Instructions: ≤2000 chars, no NUL.
- Run ids and experiment ids are hex-validated before path use (path-traversal
  safe `ExperimentStore.get`).
- Replay filenames resolve inside `data/replay` only.
- `scan_mode` and `environment` are enum-validated by Pydantic `Literal`.

## Resource limits

- `--max-budget` (USD) and `STRIX_TIMEOUT` (wall clock) bound every run;
  budget default comes from `STRIX_MAX_BUDGET`.
- Parallel futures rollouts run on cloned in-memory states — live state is
  never mutated.
- WS fan-out and subprocess output are capped; artifacts truncate at 20k chars.

## Audit trail

- Every Strix run: `run_id`, target, environment class (via registration),
  status, return code, artifacts path, timestamps — queryable at
  `GET /api/strix/runs`.
- Every approval decision: who, when, which recommendation — logged and
  broadcast.
- Every validation: persisted experiment with prediction/observation and
  inference flags.

## What CYBERMIND will never do

- Scan, attack, or probe unregistered targets.
- Execute attacker tooling against production systems.
- Auto-execute consequential defensive actions outside a registered sandbox.
- Present synthetic or replayed data as live production telemetry.
- Present heuristic stage inference as ATT&CK ground truth.
