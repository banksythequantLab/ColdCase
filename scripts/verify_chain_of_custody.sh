#!/usr/bin/env bash
# Restore the latest case snapshot from S3 and verify every evidence
# excerpt's SHA-256 hash. Exits non-zero on any mismatch.
set -euo pipefail
cd "$(dirname "$0")/.."
python src/restore_verify.py "$@"
