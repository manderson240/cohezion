#!/bin/bash
# OVERNIGHT_LEADERBOARD_CRON.sh - Continuous leaderboard submission automation
# Runs until deadline: April 6, 2026 11:59 PM PST
# Makes ACTUAL LEADERBOARD submissions (not test/benchmark)

set -e

WORKTREE="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
LOGFILE="/tmp/overnight_leaderboard_$(date +%Y%m%d).log"
PIDFILE="/tmp/overnight_leaderboard.pid"

# Track submission times to respect rate limits
declare -A LAST_SUBMIT
declare -A RATE_LIMIT_SECS=(
    ["amd-mixed-mla"]=3600    # 1 hour
    ["amd-moe-mxfp4"]=3600
    ["amd-mxfp4-mm"]=3600
)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

write_pid() {
    echo $$ > "$PIDFILE"
}

cleanup() {
    log "Shutting down..."
    rm -f "$PIDFILE"
    exit 0
}

trap cleanup EXIT INT TERM

check_rate_limit() {
    local lb=$1
    local now=$(date +%s)
    local last=${LAST_SUBMIT[$lb]:-0}
    local limit=${RATE_LIMIT_SECS[$lb]}
    local elapsed=$((now - last))
    
    if [[ $elapsed -lt $limit ]]; then
        local wait=$((limit - elapsed))
        log "   Rate limit: $lb - ${wait}s remaining"
        return 1
    fi
    return 0
}

update_last_submit() {
    local lb=$1
    LAST_SUBMIT[$lb]=$(date +%s)
}

submit_to_leaderboard() {
    local kernel=$1
    local file=$2
    local lb=$3
    local name=$4
    
    log "[$name] Attempting leaderboard submission..."
    
    if ! check_rate_limit "$lb"; then
        return 1
    fi
    
    cd "$WORKTREE/luma_speedrun/$kernel"
    
    # ACTUAL LEADERBOARD MODE - THIS COUNTS!
    if timeout 300 popcorn-cli submit "$file" \
        --mode leaderboard \
        --gpu MI355X \
        --leaderboard "$lb" \
        --no-tui 2>&1 | tee -a "$LOGFILE"; then
        
        log "   ✅ Submitted to $lb"
        update_last_submit "$lb"
        return 0
    else
        log "   ❌ Submission failed"
        return 1
    fi
}

# Main loop
log "=========================================="
log "OVERNIGHT LEADERBOARD AUTOMATION STARTED"
log "Time: $(date)"
log "Deadline: April 6, 2026 11:59 PM PST"
log "Mode: ACTUAL LEADERBOARD SUBMISSIONS"
log "=========================================="
write_pid

round=0
while true; do
    round=$((round + 1))
    log "=== Round $round ==="
    
    # Check deadline (April 6, 2026 11:59 PM PST)
    current_ts=$(date +%s)
    # PST is UTC-7 or UTC-8 depending on DST
    # April 6, 2026 23:59 PST = April 7, 2026 06:59 or 07:59 UTC
    # Using 08:00 UTC as safe cutoff
    deadline_ts=$(date -d "2026-04-07 08:00:00 UTC" +%s 2>/dev/null || echo "0")
    
    if [[ $current_ts -gt $deadline_ts ]] && [[ $deadline_ts -ne 0 ]]; then
        log "DEADLINE REACHED! Stopping."
        break
    fi
    
    submitted=0
    
    # MLA
    submit_to_leaderboard "amd-mixed-mla" "submission.py" "amd-mixed-mla" "MLA" && submitted=$((submitted + 1))
    sleep 2
    
    # MoE
    submit_to_leaderboard "amd-moe-mxfp4" "submission.py" "amd-moe-mxfp4" "MoE" && submitted=$((submitted + 1))
    sleep 2
    
    # GEMM
    submit_to_leaderboard "amd-mxfp4-mm" "submission.py" "amd-mxfp4-mm" "GEMM" && submitted=$((submitted + 1))
    
    if [[ $submitted -eq 0 ]]; then
        log "All kernels rate-limited. Sleeping 10 minutes..."
        sleep 600
    else
        log "Submitted $submitted kernel(s). Checking status..."
        sleep 120
    fi
    
    # Log status every 10 rounds
    if [[ $((round % 10)) -eq 0 ]]; then
        log ""
        log "--- STATUS UPDATE ---"
        for lb in amd-mixed-mla amd-moe-mxfp4 amd-mxfp4-mm; do
            latest=$(timeout 10 popcorn-cli submissions list --leaderboard $lb 2>/dev/null | sed -n '2p' | awk '{print $1}')
            if [[ -n "$latest" ]]; then
                status=$(timeout 10 popcorn-cli submissions list --leaderboard $lb 2>/dev/null | sed -n '2p' | awk '{print $6}')
                log "   $lb: $latest [$status]"
            fi
        done
        log "---------------------"
        log ""
    fi
done

log "=========================================="
log "AUTOMATION COMPLETE"
log "Final time: $(date)"
log "Total rounds: $round"
log "=========================================="
