#!/bin/bash
# Optimize all 3 kernels with Ralph Loop + AutoResearch

echo "🚀 Starting Optimization Sprint for All Kernels"
echo "================================================"
echo ""

BASE_DIR="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"

cd "$BASE_DIR"

# Function to optimize a kernel
optimize_kernel() {
    local kernel=$1
    local target=$2
    local current=$3
    
    echo "🔧 Optimizing ${kernel^^}..."
    echo "   Current: ${current}µs → Target: ${target}µs"
    echo ""
    
    cd "$BASE_DIR/research/challenges/luma_amd_speedrun"
    
    # Run Ralph Loop for this kernel
    timeout 3600 python3 autoresearch/ralph_main.py \
        --kernel "$kernel" \
        --max-cycles 50 \
        --coherence-threshold 0.5 \
        --stagnation-threshold 7 \
        2>&1 | tee "/tmp/ralph_${kernel}_$(date +%Y%m%d_%H%M%S).log"
    
    echo "   ✓ ${kernel^^} optimization complete"
    echo ""
}

# Run in parallel
echo "Launching parallel optimization teams..."
echo ""

# Start all three optimizations in parallel
optimize_kernel "gemm" "4.3" "22.8" &
PID_GEMM=$!

optimize_kernel "mla" "33.0" "69.7" &
PID_MLA=$!

optimize_kernel "moe" "109.8" "154.2" &
PID_MOE=$!

echo "PIDs: GEMM=$PID_GEMM MLA=$PID_MLA MoE=$PID_MOE"
echo ""
echo "Monitoring progress... (Ctrl+C to stop)"
echo ""

# Wait for all to complete
wait $PID_GEMM $PID_MLA $PID_MOE

echo ""
echo "================================================"
echo "✅ All optimizations complete!"
echo "================================================"
echo ""
echo "Check results with:"
echo "  ./luma_speedrun/task.sh status"
echo ""
