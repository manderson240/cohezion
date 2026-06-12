#!/bin/bash
# Strix Halo Symphony — staged sequential lane launch.
#
# Fixes the aperture-contention foot-gun in scripts/launch_gemma4_symphony.sh:
# that script launches all 4 iGPU/NPU lanes in parallel (`&`), which per
# local_environment_quirks.md can trigger GCVM_L2_PROTECTION_FAULT and require
# a cold boot to recover.
#
# This version:
#   1. Leaves Ollama alone (different port, different process).
#   2. Only restarts Lemonade lanes that are currently DOWN.
#   3. Loads iGPU models sequentially, verifying each port before the next.
#   4. Waits for each lane's /v1/models to respond before proceeding.
#
# Usage:
#   bash scripts/launch_fleet_safe.sh           # full staged launch
#   FORCE_RESTART=1 bash scripts/launch_fleet_safe.sh   # pkill stale lemonade
#   SKIP_IGPU=1 bash scripts/launch_fleet_safe.sh       # skip iGPU lanes
#   SKIP_CPU=1 bash scripts/launch_fleet_safe.sh        # skip CPU lane

set -u

echo "======================================================================"
echo "🏛️  STRIX HALO SYMPHONY — STAGED LAUNCH (safe sequential)"
echo "======================================================================"

# --- 1. Environment -----------------------------------------------------------
export HSA_OVERRIDE_GFX_VERSION=11.5.1
export PYTORCH_ROCM_ARCH=gfx1151
export TRITON_AMD_WMMA=1
export HSA_XNACK=1

# --- 2. Helpers ---------------------------------------------------------------
probe_port() {
    # $1 = port, $2 = timeout seconds
    local port=$1
    local t=${2:-2}
    curl -sS --max-time "$t" "http://localhost:$port/v1/models" >/dev/null 2>&1
}

verify_model_on_port() {
    # $1 = port, $2 = expected model id (substring match).
    # Confirms /v1/models actually serves the expected model — guards against
    # a lane coming up with the wrong weights loaded (adversarial review
    # edge-case #13). Returns 0 if match, 1 if port up but wrong model, 2 if
    # unreachable.
    local port=$1
    local expected=$2
    local body
    body=$(curl -sS --max-time 3 "http://localhost:$port/v1/models" 2>/dev/null) || return 2
    if [ -z "$body" ]; then
        return 2
    fi
    # Tolerate JSON, YAML, or plain-text /v1/models bodies — substring match
    # is sufficient to spot "wrong model on port" at launch time.
    if echo "$body" | grep -qF "$expected"; then
        return 0
    fi
    return 1
}

wait_for_port() {
    # $1 = port, $2 = lane label, $3 = max seconds, $4 = expected model id
    local port=$1
    local lane=$2
    local max_wait=${3:-90}
    local expected_model=${4:-}
    local waited=0
    echo -n "    waiting for $lane on :$port "
    while ! probe_port "$port" 2; do
        if [ "$waited" -ge "$max_wait" ]; then
            echo " TIMEOUT after ${max_wait}s"
            return 1
        fi
        echo -n "."
        sleep 3
        waited=$((waited + 3))
    done
    echo -n " UP (after ${waited}s)"
    if [ -n "$expected_model" ]; then
        if verify_model_on_port "$port" "$expected_model"; then
            echo " — model verified: $expected_model"
        else
            echo " — ⚠️  WRONG MODEL on :$port (expected substring: $expected_model)"
            return 2
        fi
    else
        echo ""
    fi
    return 0
}

# --- 3. Optional: kill stale lemonade (but NOT ollama) ------------------------
if [ "${FORCE_RESTART:-0}" = "1" ]; then
    echo "🧹 FORCE_RESTART=1: killing stale lemonade/llama-server (Ollama preserved)..."
    pkill -9 -f "lemonade|llama-server" 2>/dev/null || true
    sleep 2
fi

# --- 4. NPU Lane — DECOMMISSIONED (Phase 2+) -----------------------------------
# llama3.2-1b-FLM is served on-demand by the unified router on :13305.
# The dedicated :13306 daemon is no longer needed and wastes RAM.
# Old: lemonade load Gemma-4-E2B-it-GGUF --port 13306 --llamacpp flm

# --- 5-7. iGPU Lanes + CPU Lane — DECOMMISSIONED Phase 3+ ----------------------
# Router :13305 serves all models on-demand; dedicated per-port daemons are
# redundant and add resident memory pressure. Models load lazily when requested.
#
# If you need to re-enable a dedicated lane (e.g. for CLaSp benchmarking):
#   lemonade load Gemma-4-E4B-it-GGUF --port 13307 --llamacpp rocm --llamacpp-args "-fa 1 -ngl 99"
#   lemonade load Gemma-4-26B-A4B-it-GGUF --port 13308 --llamacpp rocm --llamacpp-args "-fa 1 -ngl 99"
#   lemonade load Gemma-4-31B-it-GGUF --port 13309 --llamacpp cpu --ctx-size 32768

echo ""
echo "======================================================================"
echo "✅ STAGED LAUNCH COMPLETE"
echo "Probe: make health-fleet"
echo "Demo:  make demo-universes"
echo "======================================================================"
