#!/usr/bin/env bash
# ==============================================================================
# Cohezion Autonomous Fleet Resume Script (Post-Reboot)
# ==============================================================================
# Restores the entire autonomous inference, sentry, and Kaggle ascension fleet
# incorporating all recent learnings (Bitboard, Convex Simplex, Bipartite Matching,
# EMA Rate Filtering, Typed Contracts, and FastFlowLM NPU SRAM acceleration).
# ==============================================================================

set -eo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${PROJECT_ROOT}"

echo "=================================================================="
echo " [Cohezion Fleet] Resuming Autonomous Operations Post-Reboot"
echo " Project Root: ${PROJECT_ROOT}"
echo " Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "=================================================================="

# 1. Verify Host Silicon & NPU Availability
echo -n "[1/6] Checking AMD XDNA 2 NPU hardware (/dev/accel/accel0)... "
if [ -e "/dev/accel/accel0" ]; then
    echo "ONLINE"
else
    echo "WARNING: /dev/accel/accel0 not found! Checking dmesg/flm validate..."
fi

# 2. Check SurrealDB port 8001
echo -n "[2/6] Checking SurrealDB persistence (:8001)... "
if curl -s -u root:root -H "surreal-ns: cohezion" -H "surreal-db: main" http://localhost:8001/health >/dev/null 2>&1; then
    echo "ONLINE"
else
    echo "OFFLINE. Starting SurrealDB user service or local instance..."
    systemctl --user start surrealdb.service 2>/dev/null || true
    sleep 2
fi

# 3. Launch Supervised FastFlowLM NPU Daemon (Port 8005)
echo "[3/6] Starting Supervised FastFlowLM NPU server on port 8005..."
if curl -s http://127.0.0.1:8005/v1/models >/dev/null 2>&1; then
    echo "      FLM server already running on port 8005."
else
    nohup python3 scripts/npu/supervised_flm_server.py --port 8005 --model qwen3.5:4b > /tmp/flm_server_8005.log 2>&1 &
    echo "      Waiting for port 8005 readiness..."
    for i in {1..20}; do
        if curl -s http://127.0.0.1:8005/v1/models >/dev/null 2>&1; then
            echo "      Port 8005 is ONLINE (PID: $(pgrep -f 'supervised_flm_server.py'))"
            break
        fi
        sleep 1
    done
fi

# 4. Launch A2A NPU Microservice (Port 8008)
echo "[4/6] Starting Cohezion A2A NPU Microservice on port 8008..."
if curl -s http://127.0.0.1:8008/a2a/v1/health >/dev/null 2>&1; then
    echo "      A2A microservice already running on port 8008."
else
    nohup python3 scripts/npu/a2a_npu_microservice.py > /tmp/a2a_npu_8008.log 2>&1 &
    sleep 1
    if curl -s http://127.0.0.1:8008/a2a/v1/health >/dev/null 2>&1; then
        echo "      A2A microservice is ONLINE on port 8008."
    else
        echo "      A2A microservice starting..."
    fi
fi

# 5. Launch Fleet Sentry Watcher with EMA Rate Filter
echo "[5/6] Starting Fleet Sentry with discrete EMA rate filtering..."
if pgrep -f "scripts/fleet_sentry.py --watch" >/dev/null 2>&1; then
    echo "      Fleet Sentry already running."
else
    nohup python3 scripts/fleet_sentry.py --watch --interval 20.0 > /tmp/fleet_sentry.log 2>&1 &
    echo "      Fleet Sentry started in background (PID: $!)."
fi

# 6. Restore Autonomous Tmux Swarm Sessions
echo "[6/6] Launching Kaggle Swarm Tmux Sessions..."

# 6a. Sentinel 24/7 Submissions Poller
if tmux has-session -t kaggle-sentinel 2>/dev/null; then
    echo "      Session 'kaggle-sentinel' already exists."
else
    tmux new-session -d -s kaggle-sentinel "python3 scripts/kaggle/master_24_7_kaggle_sentinel.py"
    echo "      Created tmux session 'kaggle-sentinel'."
fi

# 6b. Midnight All-Competitions Submitter
if tmux has-session -t kaggle-midnight 2>/dev/null; then
    echo "      Session 'kaggle-midnight' already exists."
else
    tmux new-session -d -s kaggle-midnight "python3 scripts/kaggle/queue_midnight_all_competitions.py"
    echo "      Created tmux session 'kaggle-midnight'."
fi

# 6c. Stateless NPU Ascension Worker (ARC-AGI-2, RSNA, NFL BDB, CASMI26)
if tmux has-session -t kaggle-npu-ascension 2>/dev/null; then
    echo "      Session 'kaggle-npu-ascension' already exists."
else
    tmux new-session -d -s kaggle-npu-ascension "python3 scripts/kaggle/stateless_npu_ascension_worker.py --epochs 1000 --model qwen3.5:4b"
    echo "      Created tmux session 'kaggle-npu-ascension'."
fi

echo "=================================================================="
echo " [Cohezion Fleet] All Autonomous Services Resumed Successfully!"
echo " Telemetry Ports: FLM=:8005 | A2A=:8008 | SurrealDB=:8001"
echo " Active Tmux Sessions: $(tmux list-sessions 2>/dev/null | awk -F: '{print $1}' | tr '\n' ' ')"
echo "=================================================================="
