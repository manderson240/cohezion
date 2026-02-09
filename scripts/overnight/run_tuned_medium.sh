#!/usr/bin/env bash
# Tuned Medium-Scale Overnight Simulation with Real-Time Ollama Analysis
#
# Launches two processes:
#   1. mass_sim_driver.py --scale medium  (simulation, ~2 hours)
#   2. analysis_watcher.py               (Ollama narratives, follows sim)
#
# Pre-flight checks: SurrealDB health, Ollama + phi3:mini, available RAM.
# Processes communicate only through SurrealDB.
#
# Usage:
#   ./scripts/overnight/run_tuned_medium.sh                  # medium (default)
#   MASS_SIM_SCALE=demo ./scripts/overnight/run_tuned_medium.sh  # demo (30s test)
#   ./scripts/overnight/run_tuned_medium.sh --scale demo --universes 3

set -euo pipefail

COHEZION_DIR="/home/mike-anderson/dev/cohezion"
LOG_DIR="${COHEZION_DIR}/data/mass_sim"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/tuned_${TIMESTAMP}.log"
SIM_LOG="${LOG_DIR}/tuned_sim_${TIMESTAMP}.log"
WATCHER_LOG="${LOG_DIR}/tuned_watcher_${TIMESTAMP}.log"
PID_FILE="${LOG_DIR}/.tuned_medium.pid"
SCALE="${MASS_SIM_SCALE:-medium}"
MIN_RAM_GB=10

cd "${COHEZION_DIR}"

# Ensure directories exist
mkdir -p "${LOG_DIR}/artifacts" "${LOG_DIR}/checkpoints/jsonl"

# ---- Logging helper ----
log() {
    echo "[$(date '+%H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

# ---- PID lock ----
if [ -f "${PID_FILE}" ]; then
    OLD_PID=$(cat "${PID_FILE}")
    if kill -0 "${OLD_PID}" 2>/dev/null; then
        log "ERROR: Tuned medium simulation already running (PID ${OLD_PID}). Exiting."
        exit 1
    fi
    rm -f "${PID_FILE}"
fi
echo $$ > "${PID_FILE}"

# ---- Cleanup on exit ----
SIM_PID=""
WATCHER_PID=""

cleanup() {
    log "Cleanup triggered..."

    # Kill watcher first (non-critical)
    if [ -n "${WATCHER_PID}" ] && kill -0 "${WATCHER_PID}" 2>/dev/null; then
        log "Stopping analysis watcher (PID ${WATCHER_PID})..."
        kill -TERM "${WATCHER_PID}" 2>/dev/null || true
        wait "${WATCHER_PID}" 2>/dev/null || true
    fi

    # Kill simulation
    if [ -n "${SIM_PID}" ] && kill -0 "${SIM_PID}" 2>/dev/null; then
        log "Stopping simulation (PID ${SIM_PID})..."
        kill -TERM "${SIM_PID}" 2>/dev/null || true
        wait "${SIM_PID}" 2>/dev/null || true
    fi

    rm -f "${PID_FILE}"
    log "Cleanup complete."
}

trap cleanup EXIT SIGTERM SIGINT

# ---- Pre-flight: RAM check ----
log "=== Pre-flight Checks ==="

AVAIL_RAM_GB=$(awk '/MemAvailable/ {printf "%.0f", $2/1048576}' /proc/meminfo)
log "Available RAM: ${AVAIL_RAM_GB} GB (minimum: ${MIN_RAM_GB} GB)"
if [ "${AVAIL_RAM_GB}" -lt "${MIN_RAM_GB}" ]; then
    log "ERROR: Insufficient RAM. Aborting."
    exit 1
fi

# ---- Pre-flight: SurrealDB ----
SURREAL_OK=false
for i in 1 2 3; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        SURREAL_OK=true
        break
    fi
    log "SurrealDB not responding (attempt ${i}/3), waiting 5s..."
    sleep 5
done

if [ "${SURREAL_OK}" = false ]; then
    # Try to restart SurrealDB if systemd service exists
    if systemctl is-active --quiet surrealdb 2>/dev/null; then
        log "Restarting SurrealDB via systemctl..."
        systemctl restart surrealdb 2>/dev/null || true
        sleep 5
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            SURREAL_OK=true
        fi
    fi

    if [ "${SURREAL_OK}" = false ]; then
        log "WARNING: SurrealDB unavailable. Simulation will use JSONL fallback."
        log "WARNING: Analysis watcher will not start (requires SurrealDB)."
    fi
fi

if [ "${SURREAL_OK}" = true ]; then
    log "SurrealDB: healthy"
fi

# ---- Pre-flight: Ollama ----
OLLAMA_OK=false
if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    OLLAMA_OK=true
    log "Ollama: healthy"

    # Pre-warm phi3:mini (load into memory)
    log "Pre-warming phi3:mini..."
    curl -sf http://localhost:11434/api/generate \
        -d '{"model":"phi3:mini","prompt":"hello","stream":false,"options":{"num_predict":1}}' \
        > /dev/null 2>&1 || true
    log "phi3:mini ready"
else
    log "WARNING: Ollama not running. Analysis watcher will not start."
fi

# ---- Start simulation ----
log ""
log "=== Starting Tuned Medium Simulation ==="
log "Scale: ${SCALE}"
log "Sim log: ${SIM_LOG}"
log "Watcher log: ${WATCHER_LOG}"
free -h | tee -a "${LOG_FILE}"
log "---"

nice -n 10 ionice -c2 -n7 \
    uv run python mass_sim_driver.py \
        --scale "${SCALE}" \
        --max-mem 100 \
        --output-dir "data/mass_sim/artifacts" \
        "$@" \
    > "${SIM_LOG}" 2>&1 &
SIM_PID=$!
log "Simulation started (PID ${SIM_PID})"

# ---- Wait for run_id to appear in sim log ----
sleep 10

RUN_ID=""
for i in $(seq 1 12); do
    if [ -f "${SIM_LOG}" ]; then
        RUN_ID=$(grep -oP 'Mass Simulation \K(mass_sim_\d+)' "${SIM_LOG}" | head -1 || true)
        if [ -n "${RUN_ID}" ]; then
            break
        fi
    fi
    sleep 5
done

if [ -z "${RUN_ID}" ]; then
    log "WARNING: Could not extract run_id from sim log after 70s."
    log "Analysis watcher will auto-discover from SurrealDB."
fi

log "Run ID: ${RUN_ID:-auto-discover}"

# ---- Start analysis watcher (only if both SurrealDB and Ollama are up) ----
if [ "${SURREAL_OK}" = true ] && [ "${OLLAMA_OK}" = true ]; then
    WATCHER_ARGS="--poll-interval 30 --idle-timeout 300"
    if [ -n "${RUN_ID}" ]; then
        WATCHER_ARGS="${WATCHER_ARGS} --run-id ${RUN_ID}"
    else
        WATCHER_ARGS="${WATCHER_ARGS} --auto"
    fi

    nice -n 15 \
        uv run python scripts/analysis_watcher.py ${WATCHER_ARGS} \
        > "${WATCHER_LOG}" 2>&1 &
    WATCHER_PID=$!
    log "Analysis watcher started (PID ${WATCHER_PID})"
else
    log "Skipping analysis watcher (SurrealDB=${SURREAL_OK}, Ollama=${OLLAMA_OK})"
fi

# ---- Wait for simulation to complete ----
log "Waiting for simulation to finish..."
SIM_EXIT=0
wait "${SIM_PID}" || SIM_EXIT=$?
SIM_PID=""

if [ "${SIM_EXIT}" -eq 0 ]; then
    log "Simulation completed successfully."
else
    log "Simulation exited with code ${SIM_EXIT}."
fi

# ---- Wait for watcher to finish (up to 10 min for final synthesis) ----
if [ -n "${WATCHER_PID}" ] && kill -0 "${WATCHER_PID}" 2>/dev/null; then
    log "Waiting up to 10 minutes for analysis watcher to finish synthesis..."
    WATCHER_DEADLINE=$(($(date +%s) + 600))
    while kill -0 "${WATCHER_PID}" 2>/dev/null; do
        if [ "$(date +%s)" -gt "${WATCHER_DEADLINE}" ]; then
            log "Watcher timeout (10 min). Sending SIGTERM."
            kill -TERM "${WATCHER_PID}" 2>/dev/null || true
            wait "${WATCHER_PID}" 2>/dev/null || true
            break
        fi
        sleep 5
    done
    wait "${WATCHER_PID}" 2>/dev/null || true
    WATCHER_PID=""
    log "Analysis watcher complete."
fi

# ---- Summary ----
log ""
log "=== Run Complete ==="
log "Simulation log: ${SIM_LOG}"
log "Watcher log: ${WATCHER_LOG}"
log "Orchestrator log: ${LOG_FILE}"
log "Artifacts: data/mass_sim/artifacts/"

if [ -f "${SIM_LOG}" ]; then
    log ""
    log "--- Simulation tail ---"
    tail -20 "${SIM_LOG}" | tee -a "${LOG_FILE}"
fi

if [ -f "${WATCHER_LOG}" ]; then
    log ""
    log "--- Watcher tail ---"
    tail -10 "${WATCHER_LOG}" | tee -a "${LOG_FILE}"
fi

exit "${SIM_EXIT}"
