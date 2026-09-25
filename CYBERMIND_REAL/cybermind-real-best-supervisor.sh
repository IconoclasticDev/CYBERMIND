#!/bin/bash
set -eo pipefail
utils=/opt/supervisor-scripts/utils
. "${utils}/logging.sh"
. "${utils}/environment.sh"
set -u
cd /workspace/cybermind/CYBERMIND_REAL
pty ./scripts/run_real_best_pipeline.sh 2>&1
