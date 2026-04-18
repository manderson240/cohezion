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

wait_for_port() {
    local port=$1
    local lane=$2
    local max_wait=${3:-90}
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
    echo " UP (after ${waited}s)"
    return 0
}

# --- 3. Optional: kill stale lemonade (but NOT ollama) ------------------------
if [ "${FORCE_RESTART:-0}" = "1" ]; then
    echo "🧹 FORCE_RESTART=1: killing stale lemonade/llama-server (Ollama preserved)..."
    pkill -9 -f "lemonade|llama-server" 2>/dev/null || true
    sleep 2
fi

# --- 4. NPU Lane (:13306) — Gemma-4-E2B ---------------------------------------
if probe_port 13306; then
    echo "🎻 NPU :13306 already UP — skipping"
else
    echo "🎻 Starting NPU lane (Gemma-4-E2B-it-GGUF via FLM)..."
    lemonade load Gemma-4-E2B-it-GGUF --port 13306 --llamacpp flm &
    wait_for_port 13306 "NPU" 60 || echo "    WARN: NPU did not come up"
fi

# --- 5. iGPU Lane 1 (:13307) — Gemma-4-E4B via ROCWMMA ------------------------
if [ "${SKIP_IGPU:-0}" = "1" ]; then
    echo "⏭️   SKIP_IGPU=1: skipping :13307 and :13308"
else
    if probe_port 13307; then
        echo "🎺 iGPU ROCWMMA :13307 already UP — skipping"
    else
        echo "🎺 Starting Steering Lane (Gemma-4-E4B, iGPU ROCWMMA)..."
        lemonade load Gemma-4-E4B-it-GGUF --port 13307 --llamacpp rocm --llamacpp-args "-fa 1 -ngl 99" &
        wait_for_port 13307 "iGPU ROCWMMA" 120 || {
            echo "    ERROR: iGPU E4B did not come up. Aborting staged launch."
            echo "    If rocm-smi shows zombie VRAM, cold-boot recovery required."
            exit 2
        }
    fi

    # --- 6. iGPU Lane 2 (:13308) — Gemma-4-26B-A4B MoE ------------------------
    if probe_port 13308; then
        echo "🏗️  iGPU Unified :13308 already UP — skipping"
    else
        echo "🏗️  Starting Building Lane (Gemma-4-26B-A4B MoE, iGPU Unified 120GB GTT)..."
        echo "    (waiting 5s post-E4B before loading 26B to avoid concurrent JIT)"
        sleep 5
        lemonade load Gemma-4-26B-A4B-it-GGUF --port 13308 --llamacpp rocm --llamacpp-args "-fa 1 -ngl 99" &
        wait_for_port 13308 "iGPU Unified" 180 || {
            echo "    ERROR: iGPU 26B did not come up. Aborting."
            exit 3
        }
    fi
fi

# --- 7. CPU Lane (:13309) — Gemma-4-31B via AVX-VNNI --------------------------
if [ "${SKIP_CPU:-0}" = "1" ]; then
    echo "⏭️   SKIP_CPU=1: skipping :13309"
else
    if probe_port 13309; then
        echo "🏛️  CPU :13309 already UP — skipping"
    else
        echo "🏛️  Starting Architect Lane (Gemma-4-31B, CPU AVX-VNNI)..."
        lemonade load Gemma-4-31B-it-GGUF --port 13309 --llamacpp cpu --ctx-size 32768 &
        wait_for_port 13309 "CPU" 120 || echo "    WARN: CPU lane did not come up"
    fi
fi

echo ""
echo "======================================================================"
echo "✅ STAGED LAUNCH COMPLETE"
echo "Probe: make health-fleet"
echo "Demo:  make demo-universes"
echo "======================================================================"
