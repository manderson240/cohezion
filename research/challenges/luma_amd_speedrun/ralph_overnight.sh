#!/bin/bash
# Ralph Loop Overnight Execution Script
# Generated: $(date)
# Purpose: Autonomous kernel optimization for AMD Speedrun competition

set -e

echo "=== Ralph Loop Overnight Run Starting ==="
echo "Timestamp: $(date)"
echo "Working directory: $(pwd)"
echo ""

# Configuration
COHERENCE_THRESHOLD=0.5
MAX_CYCLES=50
STAGNATION_THRESHOLD=7

# Create log directory
mkdir -p logs/ralph_overnight

# Function to run Ralph Loop for a kernel
run_ralph_loop() {
    local kernel=$1
    local max_cycles=$2
    local log_file="logs/ralph_overnight/${kernel}_$(date +%Y%m%d_%H%M%S).log"
    
    echo "Starting Ralph Loop for kernel: $kernel"
    echo "Max cycles: $max_cycles"
    echo "Log file: $log_file"
    echo ""
    
    cd autoresearch
    uv run python ralph_main.py \
        --kernel "$kernel" \
        --max-cycles "$max_cycles" \
        --coherence-threshold "$COHERENCE_THRESHOLD" \
        --stagnation-threshold "$STAGNATION_THRESHOLD" \
        2>&1 | tee "$log_file"
    
    cd ..
    echo "Completed Ralph Loop for $kernel at $(date)"
    echo ""
}

# Priority 1: MoE (closest to target - only ~1µs gap)
echo "=== Phase 1: MoE Optimization (Priority) ==="
run_ralph_loop "moe" 30

# Priority 2: MLA (2.1x gap - FlashAttention approach)
echo "=== Phase 2: MLA Optimization ==="
run_ralph_loop "mla" 30

# Priority 3: GEMM (3.1x gap - HipKittens DSL exploration)
echo "=== Phase 3: GEMM K-Search Exploration ==="
run_ralph_loop "gemm" 20

echo "=== Ralph Loop Overnight Run Complete ==="
echo "End timestamp: $(date)"
echo "Results logged in: logs/ralph_overnight/"

# Summary report
echo ""
echo "=== Summary Report ==="
for log in logs/ralph_overnight/*.log; do
    if [ -f "$log" ]; then
        echo "--- $(basename $log) ---"
        tail -50 "$log" | grep -E "(Best|Coherence|Improvement|Target|Complete)" || echo "(No summary lines found)"
        echo ""
    fi
done

