#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p data/raw/CIC-IDS-2018
PREFIX="${1:-}"
if ! command -v aws >/dev/null 2>&1; then echo "AWS CLI missing. Install awscli on the data/GPU host."; exit 2; fi
if [[ -n "$PREFIX" ]]; then
  aws s3 sync --no-sign-request "s3://cse-cic-ids2018/${PREFIX}" data/raw/CIC-IDS-2018/
else
  aws s3 sync --no-sign-request s3://cse-cic-ids2018/ data/raw/CIC-IDS-2018/
fi
find data/raw/CIC-IDS-2018 -type f | sort | tee data/manifests/cic2018_downloaded_files.txt
