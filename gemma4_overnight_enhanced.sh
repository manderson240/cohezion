#!/bin/bash
# gemma4_overnight_enhanced.sh - Overnight system with Gemma4 offload
# Uses Gemma4 for quick tasks, reserves kimi-k2.5:cloud for complex optimizations

set -e

WORKTREE="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
LOG="/tmp/overnight_gemma4_$(date +%Y%m%d).log"
RESULTS="/tmp/overnight_results.csv"

echo "timestamp,kernel,submission_id,status,score" > "$RESULTS"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

# Check if ollama is available
ollama_available() {
    command -v ollama > /dev/null 2>&1
}

# Use Gemma4 to analyze submission logs
analyze_with_gemma4() {
    local logfile=$1
    local kernel=$2
    
    if ! ollama_available; then
        return
    fi
    
    # Extract last 50 lines
    local last_logs=$(tail -50 "$logfile" 2>/dev/null)
    
    # Ask Gemma4 to analyze
    log "[$kernel] Querying Gemma4 for log analysis..."
    
    local prompt="Analyze these GPU kernel submission logs for $kernel. Identify errors and suggest quick fixes:\n\n$last_logs"
    
    timeout 60 ollama run gemma4 "$prompt" 2>/dev/null > /tmp/gemma4_analysis_${kernel}.txt || true
    
    if [[ -s /tmp/gemma4_analysis_${kernel}.txt ]]; then
        log "[$kernel] Gemma4 analysis:"
        head -5 /tmp/gemma4_analysis_${kernel}.txt | sed 's/^/  /' | tee -a "$LOG"
    fi
}

# Use Gemma4 to generate variant ideas
get_variant_suggestion() {
    local kernel=$1
    local current_code=$2
    
    if ! ollama_available; then
        echo ""
        return
    fi
    
    # Quick parameter suggestion - Gemma4 is fast
    local prompt="For AMD GPU $kernel optimization targeting speed, suggest one parameter to tweak: block_size, split_k, or num_warps. Respond with just: PARAMETER=VALUE"
    
    timeout 30 ollama run gemma4 "$prompt" 2>/dev/null | head -1
}

# Submit a kernel with Gemma4-enhanced error handling
submit_kernel() {
    local kernel=$1
    local subdir=$2
    local leaderboard=$3
    local variant=${4:-"submission.py"}
    
    log "[$kernel] Submitting: $variant"
    
    cd "$WORKTREE/luma_speedrun/$subdir"
    local temp_out="/tmp/submit_${kernel}_$(date +%s).out"
    
    # Submit
    timeout 600 popcorn-cli submit "$variant" \
        --mode leaderboard \
        --gpu MI355X \
        --leaderboard "$leaderboard" \
        --no-tui > "$temp_out" 2>&1 || true
    
    # Extract results
    local sub_id=$(grep -oP 'Submission #\K[0-9]+' "$temp_out" || echo "")
    
    if [[ -n "sub_id" ]]; then
        log "[$kernel] Submission ID: $sub_id"
        
        # Wait and check
        sleep 60
        local status=$(timeout 10 popcorn-cli submissions show "$sub_id" 2>/dev/null | grep "Status:" | awk '{print $2}' || echo "unknown")
        local has_lb=$(timeout 10 popcorn-cli submissions show "$sub_id" 2>/dev/null | grep -c "leaderboard on" || echo "0")
        
        log "[$kernel] Status: $status, Leaderboard: $has_lb"
        
        # Log to CSV
        echo "$(date +%s),$kernel,$sub_id,$status,$has_lb" >> "$RESULTS"
        
        # Gemma4 analysis on failures
        if [[ "$has_lb" -eq 0 ]]; then
            analyze_with_gemma4 "$temp_out" "$kernel"
        fi
        
        return 0
    else
        log "[$kernel] No submission ID - likely rate limited"
        grep -i "rate\|limit\|error" "$temp_out" | head -2 | tee -a "$LOG"
        return 1
    fi
    
    rm -f "$temp_out"
}

# Main loop
main() {
    log "=========================================="
    log "GEMMA4-ENHANCED OVERNIGHT SYSTEM"
    log "Started: $(date)"
    log "=========================================="
    
    if ollama_available; then
        log "Gemma4 available for task offload ✅"
    else
        log "Gemma4 not available - running without AI enhancement"
    fi
    
    local round=0
    
    while true; do
        round=$((round + 1))
        log ""
        log "=== ROUND $round ==="
        
        # Check deadline (April 6, 2026 11:59 PM PST)
        if [[ $(date +%s) -gt $(date -d "2026-04-07 08:00 UTC" +%s) ]]; then
            log "DEADLINE REACHED"
            break
        fi
        
        # Submit all three with staggered timing
        submit_kernel "mla" "amd-mixed-mla" "amd-mixed-mla" "submission_fixed.py" &
        sleep 60
        
        submit_kernel "moe" "amd-moe-mxfp4" "amd-moe-mxfp4" "submission.py" &
        sleep 60
        
        submit_kernel "gemm" "amd-mxfp4-mm" "amd-mxfp4-mm" "submission.py" &
        
        # Wait for all to complete
        wait
        
        # Periodic Gemma4 analysis every 5 rounds
        if [[ $((round % 5)) -eq 0 ]] && ollama_available; then
            log "Running Gemma4 strategic analysis..."
            
            # Summarize recent results
            local recent=$(tail -10 "$RESULTS")
            local prompt="Analyze these submission results and suggest strategy adjustments:\n$recent"
            timeout 60 ollama run gemma4 "$prompt" 2>/dev/null | tee -a "$LOG" | head -10 || true
        fi
        
        # Sleep 50 minutes (rate limit is 1 hour)
        log "Sleeping 50 minutes..."
        sleep 3000
    done
    
    log "=========================================="
    log "System shutdown. Total rounds: $round"
    log "Results: $RESULTS"
    log "=========================================="
}

# Check if we should start in background
if [[ "${1:-}" == "--daemon" ]]; then
    main > /dev/null 2>&1 &
    echo "Started in background. PID: $!"
    echo "Monitor: tail -f $LOG"
else
    main
fi
