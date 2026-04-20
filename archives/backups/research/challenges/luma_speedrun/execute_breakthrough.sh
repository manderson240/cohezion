#!/bin/bash
# Luma Speedrun - ACTIVE BREAKTHROUGH EXECUTION
# Run this NOW to submit all kernels and get benchmark results

set -e

BASE_DIR="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
RESULTS_FILE="$BASE_DIR/luma_speedrun/breakthrough_results_$(date +%Y%m%d_%H%M%S).json"

echo "🚀 LUMA SPEEDRUN - ACTIVE BREAKTHROUGH EXECUTION"
echo "=================================================="
echo "Started: $(date)"
echo ""

# Create results tracking
RESULTS='{}'

submit_kernel() {
    local kernel=$1
    local submission_path=$2
    local leaderboard=$3
    local current_best=$4
    
    echo ""
    echo "📤 Submitting ${kernel^^} kernel..."
    echo "   Path: $submission_path"
    echo "   Leaderboard: $leaderboard"
    echo "   Current Best: ${current_best}µs"
    echo ""
    
    # Test mode first
    echo "   Step 1: Test mode (correctness check)..."
    if popcorn-cli submit "$submission_path" \
        --mode test \
        --gpu MI355X \
        --leaderboard "$leaderboard" \
        --no-tui 2>&1 | tee /tmp/${kernel}_test.log; then
        
        echo "   ✅ Test passed!"
        
        # Benchmark mode
        echo "   Step 2: Benchmark mode (timing)..."
        if popcorn-cli submit "$submission_path" \
            --mode benchmark \
            --gpu MI355X \
            --leaderboard "$leaderboard" \
            --no-tui 2>&1 | tee /tmp/${kernel}_bench.log; then
            
            # Extract timing from log
            TIMING=$(grep -oP '\d+\.\d+(?=\s*µs)' /tmp/${kernel}_bench.log | tail -1)
            if [ -z "$TIMING" ]; then
                TIMING=$(grep -oP '\d+\.\d+(?=\s*us)' /tmp/${kernel}_bench.log | tail -1)
            fi
            
            echo "   ✅ Benchmark complete: ${TIMING:-N/A}µs"
            
            # Leaderboard submission
            echo "   Step 3: Leaderboard submission..."
            popcorn-cli submit "$submission_path" \
                --mode leaderboard \
                --gpu MI355X \
                --leaderboard "$leaderboard" \
                --no-tui 2>&1 | tee /tmp/${kernel}_leaderboard.log || true
            
            echo "   ✅ Submitted to leaderboard!"
            
            # Store results
            RESULTS=$(echo "$RESULTS" | jq --arg k "$kernel" --arg t "${TIMING:-null}" '.[$k] = {timing: $t, status: "submitted"}')
            
        else
            echo "   ❌ Benchmark failed"
            RESULTS=$(echo "$RESULTS" | jq --arg k "$kernel" '.[$k] = {timing: null, status: "benchmark_failed"}')
        fi
    else
        echo "   ❌ Test failed"
        RESULTS=$(echo "$RESULTS" | jq --arg k "$kernel" '.[$k] = {timing: null, status: "test_failed"}')
    fi
}

# Submit GEMM
cd "$BASE_DIR"
submit_kernel \
    "gemm" \
    "$BASE_DIR/luma_speedrun/amd-mxfp4-mm/submission.py" \
    "amd-mxfp4-mm" \
    "13.425"

echo ""
echo "---"

# Submit MLA
submit_kernel \
    "mla" \
    "$BASE_DIR/luma_speedrun/amd-mixed-mla/submission.py" \
    "amd-mixed-mla" \
    "69.745"

echo ""
echo "---"

# Submit MoE
submit_kernel \
    "moe" \
    "$BASE_DIR/luma_speedrun/amd-moe-mxfp4/submission.py" \
    "amd-moe-mxfp4" \
    "154.183"

echo ""
echo "=================================================="
echo "BREAKTHROUGH EXECUTION COMPLETE"
echo "=================================================="
echo "Results:"
echo "$RESULTS" | jq .
echo ""
echo "Saved to: $RESULTS_FILE"
echo "$RESULTS" > "$RESULTS_FILE"
echo ""
echo "Next steps:"
echo "1. Review results above"
echo "2. Check leaderboard rankings"
echo "3. Run optimization iteration if needed:"
echo "   ./luma_speedrun/run-parallel.sh"
echo ""
echo "Completed: $(date)"
