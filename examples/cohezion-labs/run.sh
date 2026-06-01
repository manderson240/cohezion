#!/usr/bin/env bash
# cohezion-labs unified launcher.
# Usage:
#   ./run.sh showcase            # one showcase cycle (13 capability probes) + report
#   ./run.sh eval [SEEDS]        # agentic eval harness on ManifoldEnv (default 20 seeds)
#   ./run.sh journey SESSION TASK   # capture an agentic journey (FLUME->Surreal+Obsidian)
#   ./run.sh readback SESSION    # read OTHER sessions' journeys via SurrealDB
#   ./run.sh roster              # who's alive on the cross-session bulletin
#   ./run.sh post SESSION TOPIC BODY   # post to the cross-session bulletin
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/env.sh"
cmd="${1:-help}"; shift || true

case "$cmd" in
  showcase)  bash "$HERE/showcase/run_showcase.sh" "$@" ;;
  eval)      PYTHONPATH="$CZ_SRC" "$CZ_VENV_PY" "$HERE/eval/eval_harness.py" --seeds "${1:-20}" --out "$HERE/eval/eval_output" 2>&1 | grep -viE "amdgpu"
             PYTHONPATH="$CZ_SRC" "$CZ_VENV_PY" "$HERE/eval/eval_report.py" "$HERE/eval/eval_output" 2>&1 | grep -viE "amdgpu" ;;
  journey)   PYTHONPATH="$CZ_SRC" "$CZ_VENV_PY" "$HERE/coherence/journey_roundtrip.py" --session "${1:?session}" --task "${2:?task}" 2>&1 | grep -viE "amdgpu" ;;
  readback)  PYTHONPATH="$CZ_SRC" "$CZ_VENV_PY" "$HERE/coherence/journey_roundtrip.py" --session "${1:?session}" --readback 2>&1 | grep -viE "amdgpu" ;;
  roster)    PYTHONPATH="$CZ_SRC" "$CZ_VENV_PY" "$HERE/coherence/session_bulletin.py" roster ;;
  post)      PYTHONPATH="$CZ_SRC" "$CZ_VENV_PY" "$HERE/coherence/session_bulletin.py" post --session "${1:?session}" --topic "${2:?topic}" --body "${3:?body}" ;;
  quadrature) PYTHONPATH="$CZ_SRC" "$CZ_VENV_PY" "$HERE/coherence/quadrature_nexus_view.py" --out "$HERE/coherence/quad_view.json" 2>&1 | grep -viE "amdgpu" ;;
  cosmos)    PYTHONPATH="$CZ_SRC" "$CZ_VENV_PY" "$HERE/coherence/cosmogenesis.py" --universes "${1:-6}" --out "$HERE/coherence/cosmos.json" 2>&1 | grep -viE "amdgpu" ;;
  diffusion) PYTHONPATH="$CZ_SRC" "$CZ_VENV_PY" "$HERE/coherence/diffusion_universe.py" --epochs "${1:-600}" --out "$HERE/coherence/diffusion.json" 2>&1 | grep -viE "amdgpu" ;;
  recursion) PYTHONPATH="$CZ_SRC" "$CZ_VENV_PY" "$HERE/coherence/close_mycelium_loop.py" 2>&1 | grep -viE "amdgpu|INFO" ;;
  *)         grep '^#' "$0" | sed 's/^# \?//' ;;
esac
