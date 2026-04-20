#!/bin/bash
# AUTONOMOUS_IMPROVER.sh - AI-driven overnight improvement system
# Runs continuously, submits to leaderboard, tracks results, iterates

set -e

WORKTREE="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
LOG_DIR="/tmp/autonomous_improver_$(date +%Y%m%d)"
mkdir -p "$LOG_DIR"

LOG="$LOG_DIR/main.log"
RESULTS="$LOG_DIR/results.csv"

# Initialize results file
echo "timestamp,kernel,submission_id,status,score,improvement" > "$RESULTS"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

# Submit and capture results
submit_kernel() {
    local kernel=$1
    local subdir=$2
    local leaderboard=$3
    local variant=$4
    
    log "[$kernel] Submitting variant: $variant..."
    
    cd "$WORKTREE/luma_speedrun/$subdir"
    local temp_out="$LOG_DIR/${kernel}_$(date +%s).out"
    
    # Submit with full output capture
    timeout 600 popcorn-cli submit "$variant" \
        --mode leaderboard \
        --gpu MI355X \
        --leaderboard "$leaderboard" \
        --no-tui > "$temp_out" 2>&1
    
    local result=$?
    
    # Extract submission ID
    local sub_id=$(grep -oP 'Submission #\K[0-9]+' "$temp_out" || echo "")
    
    if [[ -n "$sub_id" ]]; then
        # Check status
        sleep 60
        local status=$(timeout 15 popcorn-cli submissions show "$sub_id" 2>/dev/null | grep "Status:" | awk '{print $2}' || echo "unknown")
        local has_leaderboard=$(timeout 15 popcorn-cli submissions show "$sub_id" 2>/dev/null | grep -c "leaderboard on" || echo "0")
        
        log "[$kernel] ID: $sub_id, Status: $status, Has Leaderboard: $has_leaderboard"
        
        # Get score from list
        sleep 30
        local list_result=$(timeout 10 popcorn-cli submissions list --leaderboard "$leaderboard" 2>/dev/null | grep "^$sub_id")
        local score=$(echo "$list_result" | awk '{print $7}')
        
        echo "$(date +%s),$kernel,$sub_id,$status,$score," >> "$RESULTS"
        
        if [[ "$has_leaderboard" -gt 0 ]]; then
            log "[$kernel] ✅ SUCCESS - Leaderboard run confirmed!"
            return 0
        else
            log "[$kernel] ⚠️ Submitted but no leaderboard run"
            return 1
        fi
    else
        log "[$kernel] ❌ No submission ID extracted"
        cat "$temp_out" | tail -20 >> "$LOG"
        return 1
    fi
    
    rm -f "$temp_out"
}

# Rotate through variants
rotate_variants() {
    local kernel=$1
    local round=$2
    
    case $kernel in
        mla)
            local variants=("submission_fixed.py" "submission_sdpa.py" "submission.py")
            echo "${variants[$((round % ${#variants[@]}))]}"
            ;;
        moe)
            local variants=("submission.py" "submission_block128.py" "submission_block256.py" "submission_ultra.py")
            echo "${variants[$((round % ${#variants[@]}))]}"
            ;;
        gemm)
            local variants=("submission.py" "submission_8wave_pingpong.py" "submission_blockscale_tuned.py")
            echo "${variants[$((round % ${#variants[@]}))]}"
            ;;
    esac
}

# Main improvement loop
main() {
    log "=========================================="
    log "AUTONOMOUS IMPROVER STARTED"
    log "PID: $$"
    log "Log: $LOG"
    log "Results: $RESULTS"
    log "=========================================="
    
    local round=0
    
    while true; do
        round=$((round + 1))
        log ""
        log "=== IMPROVEMENT ROUND $round ==="
        
        # Check if deadline approaching
        if [[ $(date +%s) -gt $(date -d "2026-04-07 06:00 UTC" +%s) ]]; then
            log "DEADLINE APPROACHING! Switching to final submissions only."
        fi
        
        # MLA
        local mla_variant=$(rotate_variants mla $round)
        submit_kernel "mla" "amd-mixed-mla" "amd-mixed-mla" "$mla_variant" || true
        sleep 60
        
        # MoE
        local moe_variant=$(rotate_variants moe $round)
        submit_kernel "moe" "amd-moe-mxfp4" "amd-moe-mxfp4" "$moe_variant" || true
        sleep 60
        
        # GEMM
        local gemm_variant=$(rotate_variants gemm $round)
        submit_kernel "gemm" "amd-mxfp4-mm" "amd-mxfp4-mm" "$gemm_variant" || true
        
        # Status report every round
        log ""
        log "--- STATUS REPORT ---"
        log "Round $round complete"
        log "Total submissions logged: $(tail -n +2 $RESULTS | wc -l)"
        
        if [[ -s "$RESULTS" ]]; then
            log "Recent results:"
            tail -3 "$RESULTS" | while read line; do
                log "  $line"
            done
        fi
        log "---------------------"
        
        # Sleep before next round
        log "Sleeping 50 minutes until next round..."
        sleep 3000
    done
}

# Handle signals
cleanup() {
    log "Shutdown signal received"
    log "Total rounds completed: $round"
    log "Final results saved to: $RESULTS"
    exit 0
}
trap cleanup INT TERM EXIT

# Run
main
