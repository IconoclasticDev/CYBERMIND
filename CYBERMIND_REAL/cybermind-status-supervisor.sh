#!/bin/bash
set -eo pipefail
utils=/opt/supervisor-scripts/utils
. "${utils}/logging.sh"
. "${utils}/environment.sh"
set -u
source /venv/main/bin/activate
cd /workspace/cybermind/CYBERMIND_REAL
pty python scripts/training_status_mcp.py 2>&1
