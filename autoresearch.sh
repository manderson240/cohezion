#!/usr/bin/env bash
set -euo pipefail
# Autoresearch: E70 Triple-Node
# Target: Activate NPU for 3/3 heterogeneous compute

cd "$(dirname "$0")"

python3 e70_triple_node_experiment.py
