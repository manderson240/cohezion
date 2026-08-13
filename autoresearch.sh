#!/usr/bin/env bash
# Autoresearch benchmark runner — overnight local inference on the Strix Halo fleet.
set -euo pipefail
cd "$(dirname "$0")"

# Fast pre-checks (<1s): syntax + policy JSON validity + router liveness.
.venv/bin/python -m py_compile experiments/overnight/harness.py experiments/overnight/tasks.py
.venv/bin/python -c "import json; json.load(open('experiments/overnight/policy.json'))"
curl -sf --max-time 3 http://localhost:13305/v1/models >/dev/null || { echo "FATAL: OmniRouter :13305 down"; exit 2; }

exec .venv/bin/python experiments/overnight/harness.py
