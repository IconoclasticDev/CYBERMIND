#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
export CYBERMIND_ROLLOUT_STEPS=4
if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
exec "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 50068
