#!/bin/bash
# AGGRESSIVE EXECUTION - Can't Stop Won't Stop
# Continuous submission with improvement tracking

set -e

EMAIL="manderson240@gmail.com"
BASE_DIR="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
LOG_DIR="/home/mike-anderson/dev/cohezion/luma_speedrun/logs_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "🚀 AGGRESSIVE EXECUTION - CAN'T STOP WON'T STOP"
echo "=============================================="
echo "Started: $(date)"
echo "Email notifications: $EMAIL"
echo "Log directory: $LOG_DIR"
echo ""

# Verified best times from today's benchmarks
BEST_TIMES=(
    "gemm:22.0"
    "moe:154.2"
    "mla:69.7"
)

submit_kernel() {
    local kernel=$1
    local board=$2
    local path=$3
    local current_best=$4
    local log="$LOG_DIR/${kernel}_$(date +%H%M%S).log"
    
    echo "[$(date '+%H:%M:%S')] Submitting ${kernel^^}..."
    
    # Test first
    timeout 180 popcorn-cli submit "$path" --mode test --gpu MI355X --leaderboard "$board" --no-tui > "$log" 2>&1
    if ! grep -q "success\|✓\|successful" "$log"; then
        echo "  ❌ Test failed"
        return 1
    fi
    
    # Benchmark
    timeout 180 popcorn-cli submit "$path" --mode benchmark --gpu MI355X --leaderboard "$board" --no-tui > "$log" 2>&1
    
    # Extract timing
    local timing=$(grep -oE '⏱ [0-9]+\.[0-9]+' "$log" | head -1 | grep -oE '[0-9]+\.[0-9]+')
    if [ -z "$timing" ]; then
        timing=$(grep -oE '[0-9]+\.[0-9]+[[:space:]]*µs' "$log" | head -1 | grep -oE '[0-9]+\.[0-9]+')
    fi
    
    if [ -n "$timing" ]; then
        echo "  🎯 Timing: ${timing}µs (current best: ${current_best}µs)"
        
        # Check if improved
        if (( $(echo "$timing < $current_best" | bc -l 2>/dev/null || echo "0") )); then
            echo "  🎉 BREAKTHROUGH! Improvement: $(echo "$current_best - $timing" | bc)µs"
            
            # Submit to leaderboard
            timeout 180 popcorn-cli submit "$path" --mode leaderboard --gpu MI355X --leaderboard "$board" --no-tui >${log}.leaderboard 2>&1
            
            # Email notification
            echo "BREAKTHROUGH: ${kernel} improved from ${current_best}µs to ${timing}µs" | \
                mail -s "🚀 Luma Speedrun Breakthrough: ${kernel}" "$EMAIL" 2>/dev/null || true
            
            return 0
        else
            echo "  📊 No improvement"
        fi
    else
        echo "  ⚠ Could not extract timing"
    fi
    
    return 1
}

# Main execution loop
echo "Execution Mode: CONTINUOUS"
echo "Submitting every kernel every iteration..."
echo ""

cd "$BASE_DIR/luma_speedrun"

ITERATION=0
while true; do
    ITERATION=$((ITERATION + 1))
    echo "=============================================="
    echo "ITERATION $ITERATION - $(date)"
    echo "=============================================="
    
    # Submit all three in rapid succession
    submit_kernel "gemm" "amd-mxfp4-mm" "$BASE_DIR/luma_speedrun/amd-mxfp4-mm/submission.py" "22.0" &
    submit_kernel "moe" "amd-moe-mxfp4" "$BASE_DIR/luma_speedrun/amd-moe-mxfp4/submission.py" "154.2" &
    submit_kernel "mla" "amd-mixed-mla" "$BASE_DIR/luma_speedrun/amd-mixed-mla/submission.py" "69.7" &
    
    wait
    
    echo ""
    echo "Iteration $ITERATION complete. Waiting 10 minutes..."
    echo "Next iteration: $(date -d '+10 minutes')"
    echo ""
    
    sleep 600  # 10 minutes between iterations
done
