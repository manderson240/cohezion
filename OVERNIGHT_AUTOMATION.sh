#!/bin/bash
# OVERNIGHT_AUTOMATION.sh - Autonomous submission system for overnight operation
# Runs continuously until deadline: April 6, 2026 11:59 PM PST

set -e

# Configuration
WORKTREE="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
LOGDIR="/tmp/overnight_$(date +%Y%m%d)"
mkdir -p $LOGDIR

# Leaderboards and their rate limits (in seconds)
declare -A LEADERBOARDS=(
    ["amd-mixed-mla"]="3600"      # 1 hour
    ["amd-moe-mxfp4"]="3600"      # 1 hour
    ["amd-mxfp4-mm"]="3600"       # 1 hour
)

# Submission files to rotate through
declare -A SUBMISSIONS_MLA=(
    ["$WORKTREE/luma_speedrun/amd-mixed-mla/submission_fixed.py"]="0"
    ["$WORKTREE/luma_speedrun/amd-mixed-mla/submission_fixed_v2.py"]="0"
    ["$WORKTREE/luma_speedrun/amd-mixed-mla/submission_sdpa.py"]="0"
)

declare -A SUBMISSIONS_MOE=(
    ["$WORKTREE/luma_speedrun/amd-moe-mxfp4/submission.py"]="0"
    ["$WORKTREE/luma_speedrun/amd-moe-mxfp4/submission_block128.py"]="0"
    ["$WORKTREE/luma_speedrun/amd-moe-mxfp4/submission_block256.py"]="0"
    ["$WORKTREE/luma_speedrun/amd-moe-mxfp4/submission_ultra.py"]="0"
)

declare -A SUBMISSIONS_GEMM=(
    ["$WORKTREE/luma_speedrun/amd-mxfp4-mm/submission.py"]="0"
    ["$WORKTREE/luma_speedrun/amd-mxfp4-mm/submission_8wave_pingpong.py"]="0"
    ["$WORKTREE/luma_speedrun/amd-mxfp4-mm/submission_blockscale_tuned.py"]="0"
)

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a $LOGDIR/overnight.log
}

check_rate_limit() {
    local leaderboard=$1
    local limit_seconds=$2
    local last_file="$LOGDIR/last_${leaderboard//-/_}.txt"
    
    if [[ -f $last_file ]]; then
        local last_time=$(cat $last_file)
        local current_time=$(date +%s)
        local elapsed=$((current_time - last_time))
        
        if [[ $elapsed -lt $limit_seconds ]]; then
            local wait_time=$((limit_seconds - elapsed))
            log "   Rate limit: $leaderboard - ${wait_time}s remaining"
            return 1
        fi
    fi
    return 0
}

update_last_submit() {
    local leaderboard=$1
    echo $(date +%s) > "$LOG_DIR/last_${leaderboard//-/_}.txt"
}

submit_if_clear() {
    local leaderboard=$1
    local file=$2
    local mode=$3
    local name=$(basename $file)
    
    if ! check_rate_limit $leaderboard ${LEADERBOARDS[$leaderboard]}; then
        return 1
    fi
    
    log "   Submitting $name to $leaderboard (mode: $mode)..."
    
    cd $(dirname $file)
    
    # Try test first, then benchmark, then leaderboard
    timeout 180 popcorn-cli submit "$name" \
        --mode $mode \
        --gpu MI355X \
        --leaderboard $leaderboard \
        --no-tui 2>&1 | tee -a $LOGDIR/${leaderboard//-/_}_$(date +%H%M).log &
    
    local pid=$!
    log "   PID: $pid"
    
    update_last_submit $leaderboard
    return 0
}

# Main loop
log "========================================"
log "OVERNIGHT AUTOMATION STARTED"
log "Time: $(date)"
log "Deadline: April 6, 2026 11:59 PM PST"
log "========================================"
log ""

round=0
while true; do
    round=$((round + 1))
    log "=== ROUND $round: $(date) ==="
    
    # Check if deadline reached (April 6, 2026 11:59 PM PST = April 7, 2026 06:59:59 UTC)
    current_ts=$(date +%s)
    deadline_ts=$(date -d "2026-04-07 06:59:59 UTC" +%s 2>/dev/null || echo "0")
    
    if [[ $current_ts -gt $deadline_ts ]] && [[ $deadline_ts -ne 0 ]]; then
        log "DEADLINE REACHED! Stopping automation."
        break
    fi
    
    submitted=0
    
    # MLA submissions
    log "[MLA] Checking submissions..."
    for file in "${!SUBMISSIONS_MLA[@]}"; do
        if submit_if_clear "amd-mixed-mla" "$file" "benchmark"; then
            submitted=$((submitted + 1))
            break  # Only one per round per kernel
        fi
    done
    sleep 2
    
    # MoE submissions
    log "[MoE] Checking submissions..."
    for file in "${!SUBMISSIONS_MOE[@]}"; do
        if submit_if_clear "amd-moe-mxfp4" "$file" "benchmark"; then
            submitted=$((submitted + 1))
            break
        fi
    done
    sleep 2
    
    # GEMM submissions
    log "[GEMM] Checking submissions..."
    for file in "${!SUBMISSIONS_GEMM[@]}"; do
        if submit_if_clear "amd-mxfp4-mm" "$file" "benchmark"; then
            submitted=$((submitted + 1))
            break
        fi
    done
    
    if [[ $submitted -eq 0 ]]; then
        log "   All kernels rate-limited. Waiting 5 minutes..."
        sleep 300
    else
        log "   Submitted $submitted kernel(s). Checking status..."
        sleep 60
    fi
    
    # Log status every 10 rounds
    if [[ $((round % 10)) -eq 0 ]]; then
        log ""
        log "--- STATUS CHECK ---"
        for lb in amd-mixed-mla amd-moe-mxfp4 amd-mxfp4-mm; do
            latest=$(timeout 10 popcorn-cli submissions list --leaderboard $lb 2>/dev/null | sed -n '2p' | awk '{print $1, $5}') || latest="N/A"
            log "   $lb: $latest"
        done
        log "--------------------"
        log ""
    fi
done

log ""
log "========================================"
log "OVERNIGHT AUTOMATION COMPLETE"
log "Final time: $(date)"
log "Total rounds: $round"
log "========================================"
