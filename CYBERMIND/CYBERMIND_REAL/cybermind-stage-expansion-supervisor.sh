#!/bin/bash
set -eo pipefail
utils=/opt/supervisor-scripts/utils
. "${utils}/logging.sh"
. "${utils}/environment.sh"
set -u
cd /workspace/cybermind/CYBERMIND_REAL
pty ./scripts/run_cic2018_stage_expansion.sh 2>&1
