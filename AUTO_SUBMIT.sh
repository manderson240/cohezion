#!/bin/bash
# Auto-submit script - runs when rate limits clear
# MoE clears first (~20 min), then MLA/GEMM (~50 min)

echo "=== AUTO SUBMISSION SCRIPT ==="
echo "Started: $(date)"
echo ""

# Function to try submission
try_submit() {
    local kernel=$1
    local submission_file=$2
    local leaderboard=$3
    
    echo "Trying $kernel..."
    timeout 300 popcorn-cli submit "$submission_file" \
        --mode leaderboard --gpu MI355X --leaderboard "$leaderboard" --no-tui 2>&1 | \
        tee "/tmp/auto_${kernel}_$(date +%H%M).log" | tail -20
    
    # Check if successful (no rate limit error)
    if grep -q "Rate limit exceeded" "/tmp/auto_${kernel}_$(date +%H%M).log" 2>/dev/null; then
        echo "  -> Rate limited"
        return 1
    elif grep -q "work on another stream" "/tmp/auto_${kernel}_$(date +%H%M).log" 2>/dev/null; then
        echo "  -> Stream conflict"
        return 1
    else
        echo "  -> Submitted successfully (or processing)"
        return 0
    fi
}

BASE_DIR="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun"

# Keep trying until all submissions succeed
while true; do
    echo ""
    echo "=== Attempt $(date) ==="
    
    # Try MoE first (likely to clear first)
    if [ ! -f "/tmp/moe_success" ]; then
        if try_submit "moe" "$BASE_DIR/amd-moe-mxfp4/submission.py" "amd-moe-mxfp4"; then
            touch /tmp/moe_success
            echo "MoE submission complete!"
        fi
    fi
    
    # Try MLA
    if [ ! -f "/tmp/mla_success" ]; then
        if try_submit "mla" "$BASE_DIR/amd-mixed-mla/submission.py" "amd-mixed-mla"; then
            touch /tmp/mla_success
            echo "MLA submission complete!"
        fi
    fi
    
    # Try GEMM (multiple variants)
    if [ ! -f "/tmp/gemm_success" ]; then
        # Try main submission first
        if try_submit "gemm" "$BASE_DIR/amd-mxfp4-mm/submission.py" "amd-mxfp4-mm"; then
            touch /tmp/gemm_success
            echo "GEMM submission complete!"
        else
            # Try blockscale if main failed
            echo "  -> Trying blockscale variant..."
            if try_submit "gemm_blockscale" "$BASE_DIR/amd-mxfp4-mm/submission_blockscale_tuned.py" "amd-mxfp4-mm"; then
                touch /tmp/gemm_success
                echo "GEMM (blockscale) submission complete!"
            fi
        fi
    fi
    
    # Check if all done
    if [ -f "/tmp/moe_success" ] && [ -f "/tmp/mla_success" ] && [ -f "/tmp/gemm_success" ]; then
        echo ""
        echo "=== ALL SUBMISSIONS COMPLETE ==="
        echo "Time: $(date)"
        exit 0
    fi
    
    # Wait before retry
    echo ""
    echo "Waiting 60 seconds..."
    sleep 60
done
