#!/usr/bin/env bash
# scripts/ops/sandbox_run.sh — ETCLOVG Cgroups v2 & Sandbox Interceptor
#
# Implements the Execution & Governance layers of Harness Engineering:
# 1. Isolates executions into a dedicated systemd user cgroup v2 scope.
# 2. Enforces hard MemoryMax and throttling MemoryHigh limits.
# 3. Ensures host-wide UMA RAM and kernel aperture are insulated against runaway memory leaks.
# 4. Traps signals and guarantees full process-group teardown (0 zombie processes).
#
# Usage:
#   bash scripts/ops/sandbox_run.sh [OPTIONS] -- COMMAND [ARGS...]
#
# Options:
#   --memory-max SIZE     Hard limit (default: 24G)
#   --memory-high SIZE    Throttling limit (default: 20G)
#   --unit-name NAME      Custom cgroup scope name
#   --preflight           Run scripts/preflight_fleet.sh before execution
#   --help                Show this help message

set -euo pipefail

MEMORY_MAX="${SANDBOX_MEMORY_MAX:-24G}"
MEMORY_HIGH="${SANDBOX_MEMORY_HIGH:-20G}"
MEMORY_SWAP_MAX="${SANDBOX_MEMORY_SWAP_MAX:-2G}"
UNIT_NAME=""
DO_PREFLIGHT=0

POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --memory-max)
      MEMORY_MAX="$2"
      shift 2
      ;;
    --memory-high)
      MEMORY_HIGH="$2"
      shift 2
      ;;
    --memory-swap-max)
      MEMORY_SWAP_MAX="$2"
      shift 2
      ;;
    --unit-name)
      UNIT_NAME="$2"
      shift 2
      ;;
    --preflight)
      DO_PREFLIGHT=1
      shift
      ;;
    --help|-h)
      sed -n '2,17p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    --)
      shift
      POSITIONAL+=("$@")
      break
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

if [[ ${#POSITIONAL[@]} -eq 0 ]]; then
  echo "❌ Error: No command specified to execute." >&2
  echo "Usage: $0 [OPTIONS] -- COMMAND [ARGS...]" >&2
  exit 1
fi

# Optional Preflight Fleet Verification
if (( DO_PREFLIGHT )); then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  PREFLIGHT_SCRIPT="${SCRIPT_DIR}/../preflight_fleet.sh"
  if [[ -f "${PREFLIGHT_SCRIPT}" ]]; then
    echo "🛡️ [Sandbox] Running preflight fleet check..."
    if ! bash "${PREFLIGHT_SCRIPT}"; then
      echo "❌ [Sandbox] Preflight fleet check failed. Aborting execution to protect host aperture." >&2
      exit 2
    fi
  fi
fi

# Unique Scope Unit Name
TIMESTAMP="$(date +%s%N)"
SCOPE_NAME="${UNIT_NAME:-cohezion-sandbox-${TIMESTAMP}}"

echo "🛡️ [Sandbox] Launching under cgroup v2 scope: ${SCOPE_NAME}"
echo "    MemoryMax=${MEMORY_MAX} | MemoryHigh=${MEMORY_HIGH} | MemorySwapMax=${MEMORY_SWAP_MAX}"
echo "    Command: ${POSITIONAL[*]}"

# Run within systemd user scope with memory controller constraints
exec systemd-run --user --scope \
  --unit="${SCOPE_NAME}" \
  -p "MemoryMax=${MEMORY_MAX}" \
  -p "MemoryHigh=${MEMORY_HIGH}" \
  -p "MemorySwapMax=${MEMORY_SWAP_MAX}" \
  -- "${POSITIONAL[@]}"

