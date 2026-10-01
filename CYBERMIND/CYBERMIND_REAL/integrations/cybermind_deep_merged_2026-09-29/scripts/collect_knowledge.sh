#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/collect_public_corpus.py --knowledge-only --source ATT\&CK --source CAPEC --source NVD
