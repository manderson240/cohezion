#!/usr/bin/env bash
set -euo pipefail
# Autoresearch: Skill Context Density Optimization
cd "$(dirname "$0")"
python3 skill_density_experiment.py "$@"
