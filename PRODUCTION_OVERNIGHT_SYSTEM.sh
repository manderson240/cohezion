#!/bin/bash
# PRODUCTION_OVERNIGHT_SYSTEM.sh - Robust multi-session leaderboard automation
# Handles failures, rate limits, and concurrent sessions safely

set -euo pipefail

# Configuration
WORKTREE="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
LOCK_DIR="/tmp/luma_leaderboard_locks"
LOG_DIR="/tmp/luma_overnight_logs"
PID_FILE="/tmp/luma_overnight.pid"
STATE_FILE="/tmp/luma_overnight_state.json"

# Rate limits (seconds between submissions)
RATE_LIMIT_MLA=3600      # 1 hour
RATE_LIMIT_MOE=3600
RATE_LIMIT_GEMM=3600

# Create directories
mkdir -p "$LOCK_DIR" "$LOG_DIR"

# Logging
LOGFILE="$LOG_DIR/overnight_$(date +%Y%m%d_%H%M%S)_$$.log"
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [$$] $1"
    echo "$msg" | tee -a "$LOGFILE"
    # Also write to shared log
    echo "$msg" >> "$LOG_DIR/all_sessions.log"
}

# Cleanup on exit
cleanup() {
    log "Cleanup: removing PID file"
    rm -f "$PID_FILE"
    rm -f "$LOCK_DIR"/*.$$
}
trap cleanup EXIT INT TERM

# Check if another session is running (but allow multiple coordinated sessions)
check_other_sessions() {
    local count=$(find "$LOCK_DIR" -name "session.*" -mmin -5 2>/dev/null | wc -l)
    log "Active sessions: $count"
    if [[ $count -gt 3 ]]; then
        log "WARNING: $count sessions active. Consider reducing."
    fi
}

# Acquire lock for specific operation
acquire_lock() {
    local name=$1
    local lockfile="$LOCK_DIR/$name.lock"
    local max_wait=30
    local waited=0
    
    while [[ -f "$lockfile" ]]; do
        local pid=$(cat "$lockfile" 2>/dev/null || echo "unknown")
        if ! ps -p "$pid" > /dev/null 2>&1; then
            # Stale lock
            log "Removing stale lock for $name (PID $pid)"
            rm -f "$lockfile"
            break
        fi
        
        waited=$((waited + 1))
        if [[ $waited -ge $max_wait ]]; then
            log "Timeout waiting for lock: $name"
            return 1
        fi
        sleep 1
    done
    
    echo $$ > "$lockfile"
    return 0
}

release_lock() {
    local name=$1
    rm -f "$LOCK_DIR/$name.lock"
}

# Check rate limit with file-based tracking
check_rate_limit() {
    local kernel=$1
    local limit_var="RATE_LIMIT_${kernel^^}"
    local limit=${!limit_var:-3600}
    
    local last_file="$LOG_DIR/last_${kernel}"
    if [[ -f "$last_file" ]]; then
        local last_time=$(cat "$last_file")
        local current_time=$(date +%s)
        local elapsed=$((current_time - last_time))
        
        if [[ $elapsed -lt $limit ]]; then
            local wait_time=$((limit - elapsed))
            log "Rate limit active for $kernel: ${wait_time}s remaining"
            return 1
        fi
    fi
    return 0
}

update_last_submit() {
    local kernel=$1
    echo $(date +%s) > "$LOG_DIR/last_${kernel}"
    log "Updated last submit time for $kernel"
}

# Detect submission result from popcorn output
parse_submission_result() {
    local output=$1
    local logfile=$2
    
    if echo "$output" | grep -q "Rate limit exceeded"; then
        echo "RATE_LIMIT"
        return
    fi
    
    if echo "$output" | grep -q "submission failed"; then
        echo "FAILED"
        return
    fi
    
    if echo "$output" | grep -q "Your code contains work on another stream"; then
        echo "DISQUALIFICATION_RISK"
        return
    fi
    
    if echo "$output" | grep -q "passed"; then
        echo "SUCCESS"
        return
    fi
    
    if echo "$output" | grep -q "Status:.*done"; then
        echo "PENDING"
        return
    fi
    
    echo "UNKNOWN"
}

# Submit to leaderboard with full error handling
submit_kernel() {
    local kernel=$1
    local subdir=$2
    local file=$3
    local leaderboard=$4
    
    log "=" 
    log "[$kernel] Starting submission process"
    
    # Check rate limit
    if ! check_rate_limit "$kernel"; then
        log "[$kernel] Skipped: rate limited"
        return 1
    fi
    
    # Acquire lock
    if ! acquire_lock "$kernel"; then
        log "[$kernel] Skipped: could not acquire lock"
        return 1
    fi
    
    log "[$kernel] Lock acquired, submitting..."
    
    cd "$WORKTREE/luma_speedrun/$subdir"
    
    local temp_out="$LOG_DIR/${kernel}_submit_$$.out"
    local start_time=$(date +%s)
    
    # Run submission with timeout
    set +e
    timeout 600 popcorn-cli submit "$file" \
        --mode leaderboard \
        --gpu MI355X \
        --leaderboard "$leaderboard" \
        --no-tui > "$temp_out" 2>&1
    local exit_code=$?
    set -e
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log "[$kernel] Submission completed in ${duration}s (exit: $exit_code)"
    
    # Parse result
    local result=$(parse_submission_result "$(cat "$temp_out")" "$temp_out")
    log "[$kernel] Result: $result"
    
    # Log full output for debugging
    cat "$temp_out" >> "$LOGFILE"
    
    case $result in
        "SUCCESS")
            log "[$kernel] ✅ Submission successful!"
            update_last_submit "$kernel"
            
            # Extract submission ID
            local sub_id=$(grep -oP 'Submission #\K[0-9]+' "$temp_out" || echo "unknown")
            log "[$kernel] Submission ID: $sub_id"
            echo "$sub_id" >> "$LOG_DIR/${kernel}_submissions.txt"
            ;;
        "RATE_LIMIT")
            log "[$kernel] ⏳ Rate limited - will retry later"
            touch "$LOG_DIR/${kernel}_rate_limited"
            ;;
        "FAILED")
            log "[$kernel] ❌ Submission failed"
            echo "$(date) - FAILED: $(cat "$temp_out" | tail -5)" >> "$LOG_DIR/${kernel}_failures.txt"
            ;;
        "DISQUALIFICATION_RISK")
            log "[$kernel] ⚠️ DISQUALIFICATION RISK - stopping submissions for this kernel"
            echo "$(date)" > "$LOG_DIR/${kernel}_blocked"
            ;;
        *)
            log "[$kernel] ❓ Unknown result - may still be processing"
            ;;
    esac
    
    release_lock "$kernel"
    rm -f "$temp_out"
    
    return 0
}

# Check status of recent submissions
check_recent_status() {
    log ""
    log "=== RECENT SUBMISSION STATUS ==="
    
    for kernel in amd-mixed-mla amd-moe-mxfp4 amd-mxfp4-mm; do
        log ""
        log "[$kernel] Recent submissions:"
        
        # Get recent submissions for this leaderboard
        local short_name=$(echo "$kernel" | sed 's/amd-//;s/-/_/g')
        local sub_file="$LOG_DIR/${short_name}_submissions.txt"
        
        if [[ -f "$sub_file" ]]; then
            tail -3 "$sub_file" | while read sub_id; do
                if [[ -n "$sub_id" ]]; then
                    local status=$(timeout 10 popcorn-cli submissions show "$sub_id" 2>/dev/null | grep "Status:" | awk '{print $2}' || echo "unknown")
                    log "   $sub_id: $status"
                fi
            done
        else
            log "   No submissions recorded"
        fi
    done
    
    log ""
}

# Main loop
main() {
    log "=========================================="
    log "PRODUCTION OVERNIGHT SYSTEM STARTED"
    log "Session: $$"
    log "Start time: $(date)"
    log "Deadline: April 6, 2026 11:59 PM PST"
    log "=========================================="
    
    echo $$ > "$PID_FILE"
    touch "$LOCK_DIR/session.$$"
    
    local round=0
    
    while true; do
        round=$((round + 1))
        log ""
        log "=== ROUND $round ==="
        
        # Check deadline
        local current_ts=$(date +%s)
        local deadline_ts=$(date -d "2026-04-07 08:00:00 UTC" +%s 2>/dev/null || echo "0")
        
        if [[ $current_ts -gt $deadline_ts ]] && [[ $deadline_ts -ne 0 ]]; then
            log "DEADLINE REACHED!"
            break
        fi
        
        # Check other sessions
        check_other_sessions
        
        # Submit all three kernels
        log "Submitting all kernels..."
        
        submit_kernel "mla" "amd-mixed-mla" "submission.py" "amd-mixed-mla" &
        local pid_mla=$!
        
        submit_kernel "moe" "amd-moe-mxfp4" "submission.py" "amd-moe-mxfp4" &
        local pid_moe=$!
        
        submit_kernel "gemm" "amd-mxfp4-mm" "submission.py" "amd-mxfp4-mm" &
        local pid_gemm=$!
        
        # Wait for all to complete
        wait $pid_mla
        wait $pid_moe
        wait $pid_gemm
        
        # Periodic status check
        if [[ $((round % 5)) -eq 0 ]]; then
            check_recent_status
        fi
        
        # Log summary
        local next_check=$(date -d "+10 minutes" "+%H:%M")
        log "Round $round complete. Next check: $next_check"
        log "Sleeping 10 minutes..."
        
        sleep 600
    done
    
    log "=========================================="
    log "SYSTEM SHUTDOWN"
    log "Total rounds: $round"
    log "End time: $(date)"
    log "=========================================="
}

# Handle arguments
case "${1:-}" in
    status)
        check_recent_status
        ;;
    stop)
        log "Stopping all sessions..."
        rm -f "$LOCK_DIR"/*
        killall -f "PRODUCTION_OVERNIGHT_SYSTEM.sh" 2>/dev/null || true
        ;;
    once)
        log "Running single round..."
        submit_kernel "mla" "amd-mixed-mla" "submission.py" "amd-mixed-mla"
        submit_kernel "moe" "amd-moe-mxfp4" "submission.py" "amd-moe-mxfp4"
        submit_kernel "gemm" "amd-mxfp4-mm" "submission.py" "amd-mxfp4-mm"
        check_recent_status
        ;;
    *)
        main
        ;;
esac
