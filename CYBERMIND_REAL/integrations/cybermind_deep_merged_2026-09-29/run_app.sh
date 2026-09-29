#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r requirements-app.txt
exec uvicorn app.main:app --host 127.0.0.1 --port 8000
