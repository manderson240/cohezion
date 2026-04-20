#!/bin/bash
# Submit breakthrough results to leaderboard with improvement tracking

set -e

BASE_DIR="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun"
RESULTS_FILE="/home/mike-anderson/dev/cohezion/luma_speedrun/leaderboard_submissions.json"

echo "🚀 BREAKTHROUGH LEADERBOARD SUBMISSION"
echo "========================================"
echo "Started: $(date)"
echo ""

# Current verified bests from benchmarks
CURRENT_BESTS=(
    "gemm:22.8"
    "moe:154.2" 
    "mla:69.7"
)

# Submit each kernel if improved
submit_if_improved() {
    local kernel=$1
    local current_best=$2
    local submission_path=$3
    local leaderboard=$4
    
    echo "Submitting ${kernel^^}..."
    echo "  Current verified best: ${current_best}µs"
    
    # Run benchmark
    local timing=$(timeout 300 popcorn-cli submit "$submission_path" \
        --mode benchmark \
        --gpu MI355X \
        --leaderboard "$leaderboard" \
        --no-tui 2>&1 | tee "/tmp/${kernel}_leaderboard_$(date +%Y%m%d_%H%M%S).log")
    
    # Extract timing
    local extracted=$(echo "$timing" | grep -oE '[0-9]+\.[0-9]+' | tail -1)
    
    if [ -n "$extracted" ]; then
        echo "  New timing: ${extracted}µs"
        
        # Check if improved
        if (( $(echo "$extracted < $current_best" | bc -l) )); then
            echo "  🎉 IMPROVEMENT! Submitting to leaderboard..."
            
            # Submit to leaderboard
            popcorn-cli submit "$submission_path" \
                --mode leaderboard \
                --gpu MI355X \
                --leaderboard "$leaderboard" \
                --no-tui
                
            echo "  ✅ Leaderboard submission complete!"
            
            # Log improvement
            echo "{\"timestamp\": \"$(date -Iseconds)\", \"kernel\": \"$kernel\", \"old_best\": $current_best, \"new_best\": $extracted, \"improvement\": $(echo "$current_best - $extracted" | bc)}" >> "$RESULTS_FILE"
        else
            echo "  📊 No improvement over $current_bestµs"
        fi
    else
        echo "  ⚠ Could not extract timing"
    fi
    echo ""
}

cd "$BASE_DIR"

# Submit all three
submit_if_improved "gemm" "22.8" "$BASE_DIR/amd-mxfp4-mm/submission.py" "amd-mxfp4-mm"
submit_if_improved "moe" "154.2" "$BASE_DIR/amd-moe-mxfp4/submission.py" "amd-moe-mxfp4"
submit_if_improved "mla" "69.7" "$BASE_DIR/amd-mixed-mla/submission.py" "amd-mixed-mla"

echo "========================================"
echo "✅ All submissions complete!"
echo "Results logged to: $RESULTS_FILE"
echo ""
