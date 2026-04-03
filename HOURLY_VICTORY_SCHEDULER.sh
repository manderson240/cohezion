#!/bin/bash
# HOURLY VICTORY SCHEDULER
# Research and submit every hour on the hour
# Until: April 6, 2026 11:59 PM PST or ALL Rank 1 achieved

set -e

LOG_DIR="/tmp/hourly_victory/$(date +%Y%m%d)"
mkdir -p "$LOG_DIR"

EMAIL="manderson240@gmail.com"
BASE_DIR="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun"

# Victory tracking
VICTORY_FILE="/tmp/victory_status.json"
MOE_WON=false
MLA_WON=false
GEMM_WON=false

# Targets
MOE_TARGET="107.345"
MLA_TARGET="12.685"
GEMM_TARGET="1.000"

log_hourly() {
    local msg="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $msg" | tee -a "$LOG_DIR/hourly.log"
}

send_hourly_email() {
    local subject="$1"
    local body="$2"
    echo "$body" | mail -s "$subject" "$EMAIL" 2>/dev/null || true
}

wait_for_next_hour() {
    local current_min=$(date +%M)
    local current_sec=$(date +%S)
    local sleep_min=$((60 - 10#$current_min))
    local sleep_sec=$((60 - 10#$current_sec))
    local total_sleep=$((sleep_min * 60 + sleep_sec))
    
    if [ "$total_sleep" -gt 3600 ]; then
        total_sleep=0
    fi
    
    log_hourly "⏰ Sleeping $total_sleep seconds until next hour..."
    sleep "$total_sleep"
}

run_submission_cycle() {
    local hour=$(date +%H)
    local cycle="$1"
    
    log_hourly ""
    log_hourly "═══════════════════════════════════════════════"
    log_hourly "HOUR $hour - CYCLE $cycle - $(date)"
    log_hourly "═══════════════════════════════════════════════"
    
    # Check current victories
    check_victories
    
    # If all won, exit
    if [ "$MOE_WON" = true ] && [ "$MLA_WON" = true ] && [ "$GEMM_WON" = true ]; then
        log_hourly "🏆 ALL KERNELS AT RANK 1 - TOTAL VICTORY!"
        send_hourly_email "🏆🏆🏆 TOTAL VICTORY! All Rank 1!" "Mission accomplished! All kernels Rank 1!"
        exit 0
    fi
    
    # Strategy: Every hour, try a different kernel
    # Hour rotation: MLA -> GEMM -> MoE -> repeat
    local kernel_num=$((10#$hour % 3))
    
    case $kernel_num in
        0)
            if [ "$MLA_WON" = false ]; then
                try_kernel "mla" "$BASE_DIR/amd-mixed-mla/submission.py" "amd-mixed-mla" "$MLA_TARGET"
            fi
            ;;
        1)
            if [ "$GEMM_WON" = false ]; then
                try_kernel "gemm" "$BASE_DIR/amd-mxfp4-mm/submission.py" "amd-mxfp4-mm" "$GEMM_TARGET"
            fi
            ;;
        2)
            if [ "$MOE_WON" = false ]; then
                try_kernel "moe" "$BASE_DIR/amd-moe-mxfp4/submission.py" "amd-moe-mxfp4" "$MOE_TARGET"
            fi
            ;;
    esac
}

try_kernel() {
    local kernel="$1"
    local file="$2"
    local leaderboard="$3"
    local target="$4"
    
    log_hourly "🔬 TESTING $kernel..."
    
    # Test mode (unlimited, ~2min)
    if timeout 180 popcorn-cli submit "$file" --mode test --gpu MI355X --leaderboard "$leaderboard" --no-tui > "$LOG_DIR/${kernel}_test_$(date +%H).log" 2>&1; then
        log_hourly "✅ $kernel TEST PASSED"
    else
        log_hourly "❌ $kernel TEST FAILED"
        return 1
    fi
    
    # Benchmark mode (unlimited, ~5min)
    log_hourly "⏱️ BENCHMARKING $kernel..."
    if timeout 300 popcorn-cli submit "$file" --mode benchmark --gpu MI355X --leaderboard "$leaderboard" --no-tui > "$LOG_DIR/${kernel}_benchmark_$(date +%H).log" 2>&1; then
        log_hourly "✅ $kernel BENCHMARK SUCCESS"
        
        # Extract timing
        local timing=$(grep -oE '[0-9]+\.[0-9]+\s*±' "$LOG_DIR/${kernel}_benchmark_$(date +%H).log" | head -1 | grep -oE '[0-9]+\.[0-9]+' || echo "999999")
        log_hourly "⏱️ $kernel timing: ${timing}µs (target: ${target}µs)"
        
        # Check if beats target
        if (( $(echo "$timing < $target" | bc -l) )); then
            log_hourly "🎉 $kernel BEATS TARGET! $timingµs < $targetµs"
            
            # Submit to leaderboard
            log_hourly "🚀 SUBMITTING $kernel TO LEADERBOARD..."
            if timeout 300 popcorn-cli submit "$file" --mode leaderboard --gpu MI355X --leaderboard "$leaderboard" --no-tui > "$LOG_DIR/${kernel}_leaderboard_$(date +%H).log" 2>&1; then
                log_hourly "✅ $kernel LEADERBOARD SUBMITTED!"
                send_hourly_email "🏆 BREAKTHROUGH: $kernel Rank 1!" "$kernel achieved $timingµs (target was $targetµs) at $(date)"
                
                # Mark victory
                case $kernel in
                    moe) MOE_WON=true ;;
                    mla) MLA_WON=true ;;
                    gemm) GEMM_WON=true ;;
                esac
            fi
        fi
    else
        log_hourly "⚠️ $kernel BENCHMARK ISSUE"
    fi
}

check_victories() {
    # Load previous victories if exist
    if [ -f "$VICTORY_FILE" ]; then
        source "$VICTORY_FILE" 2>/dev/null || true
    fi
    
    log_hourly "📊 VICTORY STATUS:"
    log_hourly "  MoE: $([ "$MOE_WON" = true ] && echo '✅ RANK 1' || echo '⏳ In Progress')"
    log_hourly "  MLA: $([ "$MLA_WON" = true ] && echo '✅ RANK 1' || echo '⏳ In Progress')"
    log_hourly "  GEMM: $([ "$GEMM_WON" = true ] && echo '✅ RANK 1' || echo '⏳ In Progress')"
}

save_victories() {
    echo "MOE_WON=$MOE_WON" > "$VICTORY_FILE"
    echo "MLA_WON=$MLA_WON" >> "$VICTORY_FILE"
    echo "GEMM_WON=$GEMM_WON" >> "$VICTORY_FILE"
    echo "LAST_UPDATED=$(date)" >> "$VICTORY_FILE"
}

# Main loop
main() {
    log_hourly "🔥🔥🔥 HOURLY VICTORY SCHEDULER STARTED 🔥🔥🔥"
    log_hourly "Mode: Submit every hour on the hour"
    log_hourly "Until: April 6, 2026 11:59 PM PST"
    log_hourly "Email: $EMAIL"
    log_hourly ""
    
    local cycle=0
    
    while true; do
        cycle=$((cycle + 1))
        
        # Skip first wait if we're already near an hour
        if [ "$cycle" -gt 1 ]; then
            wait_for_next_hour
        fi
        
        run_submission_cycle "$cycle"
        save_victories
        
        # Deadline check
        local current_date=$(date +%Y%m%d)
        if [ "$current_date" -ge "20260407" ]; then
            log_hourly "⏰ DEADLINE PASSED - Stopping scheduler"
            send_hourly_email "⏰ Hourly Scheduler Stopped" "Deadline passed. Final status: MoE=$MOE_WON, MLA=$MLA_WON, GEMM=$GEMM_WON"
            exit 0
        fi
        
        log_hourly "✅ Hour complete. Next submission in ~1 hour."
    done
}

# Trap to save state on exit
trap 'save_victories; log_hourly "Scheduler stopped at $(date)"; exit 0' INT TERM

main "$@"
