#!/usr/bin/env bash
# Storage lifecycle monitor - checks disk usage and alerts on threshold breaches
# Usage: ./storage_lifecycle.sh [--json]

set -euo pipefail

# Output mode
JSON_MODE=false
if [[ ${1:-} == "--json" ]]; then
    JSON_MODE=true
fi

# Paths
GUARDIAN_EVENTS="data/guardian_events.jsonl"
SYSLOG_DIR="/var/log"
JOURNAL_DIR="/var/log/journal"
CRASH_DIR="/var/crash"
SURREALDB_DIR="data/surrealdb"
VAULT_DIR="$HOME/vaults/cohezion-vault"
ARCHIVES_DIR="data/archives"

# Storage budgets (in bytes)
# Format: path|budget|alert_threshold|description
declare -A BUDGETS=(
    ["$JOURNAL_DIR"]="2147483648|1610612736|System journal"           # 2GB|1.5GB
    ["$SYSLOG_DIR/syslog*"]="524288000|419430400|Syslog rotations"    # 500MB|400MB
    ["$CRASH_DIR"]="104857600|83886080|Crash reports"                 # 100MB|80MB
    ["$SURREALDB_DIR"]="524288000|419430400|SurrealDB data"           # 500MB|400MB
    ["$VAULT_DIR"]="1073741824|858993459|Cohezion vault"              # 1GB|800MB
    ["$ARCHIVES_DIR"]="1073741824|858993459|Log archives"             # 1GB|800MB
    ["$SYSLOG_DIR"]="3221225472|2684354560|Total /var/log"            # 3GB|2.5GB
)

# ANSI color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Get disk usage in bytes (handles wildcards and missing directories)
get_disk_usage() {
    local path="$1"
    local size=0

    # Check if path contains wildcard
    if [[ "$path" == *\** ]]; then
        # Intentionally unquoted: glob must expand for du to match files
        # BUDGETS paths are hardcoded constants (no user input), so this is safe
        size=$(du -scb $path 2>/dev/null | tail -1 | awk '{print $1}')
    elif [[ -d "$path" ]]; then
        # Directory - get total size
        size=$(du -sb "$path" 2>/dev/null | awk '{print $1}')
    elif [[ -f "$path" ]]; then
        # Single file
        size=$(stat -c%s "$path" 2>/dev/null)
    fi

    # Ensure we return a valid integer (default to 0 if empty or error)
    echo "${size:-0}"
}

# Format bytes to human-readable
format_bytes() {
    local bytes="$1"
    if (( bytes < 1024 )); then
        echo "${bytes}B"
    elif (( bytes < 1048576 )); then
        echo "$(( bytes / 1024 ))KB"
    elif (( bytes < 1073741824 )); then
        echo "$(( bytes / 1048576 ))MB"
    else
        echo "$(( bytes / 1073741824 ))GB"
    fi
}

# Log warning event to guardian events file
log_warning() {
    local area="$1"
    local current="$2"
    local threshold="$3"
    local budget="$4"
    local percent="$5"

    mkdir -p "$(dirname "$GUARDIAN_EVENTS")"

    local event="{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"type\":\"storage_warning\",\"area\":\"$area\",\"current_bytes\":$current,\"threshold_bytes\":$threshold,\"budget_bytes\":$budget,\"usage_percent\":$percent}"

    echo "$event" >> "$GUARDIAN_EVENTS"
}

# Send desktop notification
send_notification() {
    local message="$1"

    if command -v notify-send &> /dev/null; then
        notify-send -u normal "Storage Warning" "$message" 2>/dev/null || true
    fi
}

# Check for oversized syslog files (early warning of crash loop)
check_oversized_syslogs() {
    local warnings=()

    for file in /var/log/syslog*; do
        if [[ ! -f "$file" ]]; then
            continue
        fi

        # Get size for alerting purposes
        local size
        if [[ "$file" == *.gz ]]; then
            # Use on-disk size for compressed files (alerts on actual disk impact)
            size=$(stat -c%s "$file" 2>/dev/null || echo "0")
        else
            size=$(stat -c%s "$file" 2>/dev/null || echo "0")
        fi

        # Alert if > 200MB (logical size)
        if (( size > 209715200 )); then
            local size_mb=$((size / 1048576))
            warnings+=("$file is ${size_mb}MB (potential crash loop)")
        fi
    done

    if [[ ${#warnings[@]} -gt 0 ]]; then
        for warning in "${warnings[@]}"; do
            if [[ "$JSON_MODE" == "false" ]]; then
                echo -e "${YELLOW}⚠${NC}  $warning"
            fi
        done
        return 1
    fi

    return 0
}

# Main check function
check_storage() {
    local total_warnings=0
    local warnings=()

    for path in "${!BUDGETS[@]}"; do
        IFS='|' read -r budget threshold description <<< "${BUDGETS[$path]}"

        # Get current usage
        local current
        current=$(get_disk_usage "$path")

        # Calculate percentage
        local percent=0
        if (( budget > 0 )); then
            percent=$(( (current * 100) / budget ))
        fi

        # Check if over threshold
        if (( current >= threshold )); then
            total_warnings=$((total_warnings + 1))
            local warning="$description: $(format_bytes $current) / $(format_bytes $budget) (${percent}%)"
            warnings+=("$warning")

            # Log to guardian events
            log_warning "$description" "$current" "$threshold" "$budget" "$percent"

            # Send notification on first warning
            if (( total_warnings == 1 )); then
                send_notification "$warning"
            fi
        fi
    done

    # Check for oversized syslogs
    if ! check_oversized_syslogs; then
        total_warnings=$((total_warnings + 1))
    fi

    # Output results
    if [[ "$JSON_MODE" == "true" ]]; then
        # JSON output for machine consumption
        echo -n '{"timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","warnings":'$total_warnings',"status":"'
        if (( total_warnings > 0 )); then
            echo -n 'WARNING'
        else
            echo -n 'OK'
        fi
        echo -n '","areas":['

        local first=true
        for path in "${!BUDGETS[@]}"; do
            IFS='|' read -r budget threshold description <<< "${BUDGETS[$path]}"
            local current
            current=$(get_disk_usage "$path")
            local percent=$(( (current * 100) / budget ))

            if [[ "$first" == "true" ]]; then
                first=false
            else
                echo -n ","
            fi

            echo -n '{"area":"'$description'","current_bytes":'$current',"budget_bytes":'$budget',"threshold_bytes":'$threshold',"percent":'$percent',"over_threshold":'
            if (( current >= threshold )); then
                echo -n 'true'
            else
                echo -n 'false'
            fi
            echo -n '}'
        done

        echo ']}'
    else
        # Human-readable output
        if (( total_warnings > 0 )); then
            echo -e "${RED}⚠ Storage warnings detected: $total_warnings${NC}"
            echo ""
            for warning in "${warnings[@]}"; do
                echo -e "  ${YELLOW}⚠${NC}  $warning"
            done
            echo ""
            echo "Events logged to: $GUARDIAN_EVENTS"
        else
            echo -e "${GREEN}✓${NC} Storage usage within budgets"
        fi

        # Summary
        echo ""
        echo "Storage Summary:"
        echo "┌──────────────────────────┬──────────┬──────────┬────────┐"
        echo "│ Area                     │ Current  │ Budget   │ Usage  │"
        echo "├──────────────────────────┼──────────┼──────────┼────────┤"

        for path in "${!BUDGETS[@]}"; do
            IFS='|' read -r budget threshold description <<< "${BUDGETS[$path]}"
            local current
            current=$(get_disk_usage "$path")
            local percent=$(( (current * 100) / budget ))

            printf "│ %-24s │ %8s │ %8s │ %5s%% │\n" \
                "$description" \
                "$(format_bytes $current)" \
                "$(format_bytes $budget)" \
                "$percent"
        done

        echo "└──────────────────────────┴──────────┴──────────┴────────┘"
    fi

    # Exit code: 0 = OK, 1 = warnings
    if (( total_warnings > 0 )); then
        return 1
    else
        return 0
    fi
}

# Run the check
check_storage
