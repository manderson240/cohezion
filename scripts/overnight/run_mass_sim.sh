#!/usr/bin/env bash
# Overnight Mass Simulation Runner
# Schedule: crontab -e -> 30 2 * * * /home/mike-anderson/dev/cohezion/scripts/overnight/run_mass_sim.sh
#
# Designed for unattended operation with:
#   - OOM protection (max 100GB RSS, auto-scales batch size)
#   - Graceful SIGTERM handling
#   - Full logging to data/mass_sim/simulation.log
#   - Process isolation via nice/ionice
#   - Automatic cleanup of stale checkpoints
#
# Scale tiers:
#   demo      = ~10 seconds  (100 agents x 1K epochs x 10 universes)
#   medium    = ~2 minutes   (1K agents x 10K epochs x 100 universes)
#   overnight = ~3 hours     (10K agents x 100K epochs x 1K universes)

set -euo pipefail

COHEZION_DIR="/home/mike-anderson/dev/cohezion"
LOG_DIR="${COHEZION_DIR}/data/mass_sim"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/overnight_${TIMESTAMP}.log"
PID_FILE="${LOG_DIR}/.mass_sim.pid"
SCALE="${MASS_SIM_SCALE:-medium}"

cd "${COHEZION_DIR}"

# Create directories
mkdir -p "${LOG_DIR}/artifacts" "${LOG_DIR}/checkpoints/jsonl"

# Check for already-running instance
if [ -f "${PID_FILE}" ]; then
    OLD_PID=$(cat "${PID_FILE}")
    if kill -0 "${OLD_PID}" 2>/dev/null; then
        echo "Mass simulation already running (PID ${OLD_PID}), exiting." | tee -a "${LOG_FILE}"
        exit 0
    fi
    rm -f "${PID_FILE}"
fi

# Write PID
echo $$ > "${PID_FILE}"
trap "rm -f ${PID_FILE}" EXIT

# System status before run
echo "=== Mass Simulation Starting ===" | tee "${LOG_FILE}"
echo "Timestamp: ${TIMESTAMP}" | tee -a "${LOG_FILE}"
echo "Scale: ${SCALE}" | tee -a "${LOG_FILE}"
free -h | tee -a "${LOG_FILE}"
echo "---" | tee -a "${LOG_FILE}"

# Run with low priority to avoid starving interactive sessions
# ionice: best-effort, nice: +10 priority
exec nice -n 10 ionice -c2 -n7 \
    uv run python mass_sim_driver.py \
        --scale "${SCALE}" \
        --max-mem 100 \
        --output-dir "data/mass_sim/artifacts" \
    2>&1 | tee -a "${LOG_FILE}"
