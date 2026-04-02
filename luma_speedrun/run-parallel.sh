#!/bin/bash
# Launch all Luma Speedrun agents in parallel

set -e

BASE_DIR="/home/mike-anderson/dev/cohezion"
LOG_DIR="$BASE_DIR/luma_speedrun/agent_logs"
mkdir -p "$LOG_DIR"

echo "🚀 Luma Speedrun: Launching Parallel Agent Teams"
echo "=================================================="
echo ""

# Function to run agent
run_agent() {
    local name=$1
    local dir=$2
    local cmd=$3
    local log="$LOG_DIR/${name}_$(date +%Y%m%d_%H%M%S).log"
    
    echo "[$name] Starting..."
    cd "$BASE_DIR/$dir"
    eval "$cmd" > "$log" 2>&1 &
    echo $!  # Return PID
}

# Launch GEMM Team
PID_GEMM_PRIMARY=$(run_agent \
    "gemm-claude" \
    ".worktrees/luma-breakthrough-sprint" \
    "python luma_speedrun/autoresearch/driver.py --kernel gemm --max-cycles 20")

PID_GEMM_KSEARCH=$(run_agent \
    "gemm-autoresearch" \
    "research/challenges/luma_amd_speedrun" \
    "python autokernel.py --kernel gemm --cycles 15")

# Launch MLA Team
PID_MLA=$(run_agent \
    "mla-claude" \
    ".worktrees/luma-breakthrough-sprint" \
    "python luma_speedrun/autoresearch/driver.py --kernel mla --max-cycles 20")

# Launch MoE Team
PID_MOE=$(run_agent \
    "moe-claude" \
    ".worktrees/luma-breakthrough-sprint" \
    "python luma_speedrun/autoresearch/driver.py --kernel moe --max-cycles 20")

PID_MOE_SPEC=$(run_agent \
    "moe-specialist" \
    "research/challenges/luma_amd_speedrun/kernels/moe-mxfp4" \
    "python sweep_ksplit.py --output json")

echo ""
echo "✅ All agents launched!"
echo ""
echo "PIDs:"
echo "  GEMM (Claude):     $PID_GEMM_PRIMARY"
echo "  GEMM (Autoresearch): $PID_GEMM_KSEARCH"
echo "  MLA (Claude):       $PID_MLA"
echo "  MoE (Claude):       $PID_MOE"
echo "  MoE (Specialist):   $PID_MOE_SPEC"
echo ""
echo "Logs: $LOG_DIR"
echo ""
echo "Monitor: tail -f $LOG_DIR/*.log"
echo ""
echo "Press Ctrl+C to stop all agents..."

# Wait for all agents
wait $PID_GEMM_PRIMARY $PID_GEMM_KSEARCH $PID_MLA $PID_MOE $PID_MOE_SPEC

echo ""
echo "=================================================="
echo "All agents completed!"
echo "Check results in: $LOG_DIR"
