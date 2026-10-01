#!/bin/bash
set -eo pipefail
utils=/opt/supervisor-scripts/utils
. "${utils}/logging.sh"
. "${utils}/environment.sh"
set -u
cd /workspace/cybermind/CYBERMIND_REAL
pty ./scripts/run_economy_full_dataset.sh 2>&1
