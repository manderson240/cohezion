#!/usr/bin/env bash
# service_guardian.sh - Lightweight crash-loop detection and prevention
#
# SECONDARY safety net for Cohezion services. The PRIMARY prevention is
# StartLimitBurst/StartLimitIntervalSec in each service's [Unit] section.
#
# This guardian catches edge cases:
#   - Services without proper restart limits
#   - Slow-burn crash loops that stay under burst thresholds
#   - Manual restarts of failed services
#   - Disk usage anomalies in the SurrealDB data directory
#
# Privilege boundary:
#   - User services (cohezion-lab, ngrok-*): can stop directly
#   - System services (cohezion-surreal): can only LOG and notify
#
# No Python dependencies. No cohezion imports. Survives any codebase breakage.

set -euo pipefail

# --- Configuration ---
RESTART_THRESHOLD=10          # Alert if NRestarts > this since boot
DATA_DIR="/home/mike-anderson/dev/cohezion/data/surrealdb"
FILE_COUNT_THRESHOLD=10000    # Alert if > this many files in data dir
DISK_SIZE_THRESHOLD_MB=1024   # Alert if data dir > 1GB
EVENTS_FILE="/home/mike-anderson/dev/cohezion/data/guardian_events.jsonl"

# Services to monitor
USER_SERVICES=(
    "cohezion-lab.service"
    "ngrok-tunnel.service"
    "ngrok-watchdog.service"
    "cohezion-guardian.service"
)

SYSTEM_SERVICES=(
    "cohezion-surreal.service"
)

# --- Helper functions ---
timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log_event() {
    local service="$1"
    local event="$2"
    local action="$3"
    local restarts="${4:-0}"
    local details="${5:-}"

    local json="{\"timestamp\":\"$(timestamp)\",\"service\":\"${service}\",\"event\":\"${event}\",\"action\":\"${action}\",\"restarts\":${restarts},\"details\":\"${details}\"}"

    # Write to events file
    echo "$json" >> "$EVENTS_FILE"

    # Also log to journal via stderr (captured by systemd)
    echo "GUARDIAN: ${event} - ${service} - ${action} - ${details}" >&2
}

notify_user() {
    local title="$1"
    local body="$2"

    # Desktop notification (best effort, may fail if no display)
    if command -v notify-send &>/dev/null; then
        DISPLAY=:0 notify-send --urgency=critical "Cohezion Guardian: ${title}" "${body}" 2>/dev/null || true
    fi
}

# --- Check: Service restart count ---
check_restarts() {
    local service="$1"
    local scope="$2"  # "user" or "system"
    local cmd_prefix=""

    if [[ "$scope" == "user" ]]; then
        cmd_prefix="systemctl --user"
    else
        cmd_prefix="systemctl"
    fi

    # Check if service exists
    if ! $cmd_prefix list-unit-files "$service" &>/dev/null; then
        return 0
    fi

    local nrestarts
    nrestarts=$($cmd_prefix show "$service" -p NRestarts --value 2>/dev/null || echo "0")

    if [[ "$nrestarts" -gt "$RESTART_THRESHOLD" ]]; then
        if [[ "$scope" == "user" ]]; then
            $cmd_prefix stop "$service" 2>/dev/null || true
            log_event "$service" "high_restarts" "stopped" "$nrestarts" "NRestarts=${nrestarts} exceeds threshold=${RESTART_THRESHOLD}"
            notify_user "Service Stopped" "${service}: ${nrestarts} restarts detected. Service stopped."
        else
            log_event "$service" "high_restarts" "alert" "$nrestarts" "NRestarts=${nrestarts} exceeds threshold=${RESTART_THRESHOLD} (system service - cannot stop)"
            notify_user "High Restarts" "${service}: ${nrestarts} restarts detected. Manual intervention needed (system service)."
        fi
        return 1
    fi

    return 0
}

# --- Check: Service in crash-loop state ---
check_crash_loop() {
    local service="$1"
    local scope="$2"
    local cmd_prefix=""

    if [[ "$scope" == "user" ]]; then
        cmd_prefix="systemctl --user"
    else
        cmd_prefix="systemctl"
    fi

    local active_state sub_state result
    active_state=$($cmd_prefix show "$service" -p ActiveState --value 2>/dev/null || echo "unknown")
    sub_state=$($cmd_prefix show "$service" -p SubState --value 2>/dev/null || echo "unknown")
    result=$($cmd_prefix show "$service" -p Result --value 2>/dev/null || echo "unknown")

    # Detect auto-restart loop: service is in activating/auto-restart with exit-code result
    if [[ "$active_state" == "activating" && "$sub_state" == "auto-restart" && "$result" == "exit-code" ]]; then
        if [[ "$scope" == "user" ]]; then
            $cmd_prefix stop "$service" 2>/dev/null || true
            log_event "$service" "crash_loop" "stopped" "0" "State: ${active_state}/${sub_state}, Result: ${result}"
            notify_user "Crash Loop Detected" "${service} is crash-looping. Service stopped."
        else
            log_event "$service" "crash_loop" "alert" "0" "State: ${active_state}/${sub_state}, Result: ${result} (system service - cannot stop)"
            notify_user "Crash Loop Detected" "${service} is crash-looping. Manual intervention needed (system service)."
        fi
        return 1
    fi

    return 0
}

# --- Check: Disk usage in SurrealDB data directory ---
check_disk_usage() {
    if [[ ! -d "$DATA_DIR" ]]; then
        return 0
    fi

    # Check file count
    local file_count
    file_count=$(find "$DATA_DIR" -maxdepth 1 -type f 2>/dev/null | wc -l)

    if [[ "$file_count" -gt "$FILE_COUNT_THRESHOLD" ]]; then
        log_event "surrealdb-data" "disk_alert" "alert" "0" "File count ${file_count} exceeds threshold ${FILE_COUNT_THRESHOLD}"
        notify_user "Disk Alert" "SurrealDB data dir has ${file_count} files (threshold: ${FILE_COUNT_THRESHOLD})"
        return 1
    fi

    # Check directory size
    local size_kb
    size_kb=$(du -sk "$DATA_DIR" 2>/dev/null | cut -f1)
    local size_mb=$((size_kb / 1024))

    if [[ "$size_mb" -gt "$DISK_SIZE_THRESHOLD_MB" ]]; then
        log_event "surrealdb-data" "disk_alert" "alert" "0" "Size ${size_mb}MB exceeds threshold ${DISK_SIZE_THRESHOLD_MB}MB"
        notify_user "Disk Alert" "SurrealDB data dir is ${size_mb}MB (threshold: ${DISK_SIZE_THRESHOLD_MB}MB)"
        return 1
    fi

    return 0
}

# --- Main ---
main() {
    local issues_found=0

    # Check user services
    for service in "${USER_SERVICES[@]}"; do
        check_restarts "$service" "user" || issues_found=1
        check_crash_loop "$service" "user" || issues_found=1
    done

    # Check system services
    for service in "${SYSTEM_SERVICES[@]}"; do
        check_restarts "$service" "system" || issues_found=1
        check_crash_loop "$service" "system" || issues_found=1
    done

    # Check disk usage
    check_disk_usage || issues_found=1

    # Check storage lifecycle budgets
    local storage_exit=0
    timeout 10s bash scripts/maintenance/storage_lifecycle.sh --json >/dev/null 2>&1 || storage_exit=$?
    if [[ $storage_exit -eq 124 ]]; then
        log_event "guardian" "storage_timeout" "warn" "10" "Storage check timed out"
    elif [[ $storage_exit -eq 1 ]]; then
        # Exit code 1 means warnings detected (already logged by storage_lifecycle.sh)
        issues_found=1
    fi

    # Log healthy state (for dashboarding)
    if [[ "$issues_found" -eq 0 ]]; then
        log_event "guardian" "health_check" "ok" "0" "All services healthy"
    fi

    exit 0  # Always exit 0 — guardian should never fail the timer
}

main "$@"
