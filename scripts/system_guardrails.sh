#!/bin/bash
# System Guardrails for COHEZION Overnight Simulations
# Prevents OOM, limits concurrent processes, uses local Ollama

set -e

# Memory thresholds (leave 20GB headroom)
MAX_MEMORY_PERCENT=85
MIN_FREE_GB=20

# Process limits
MAX_CONCURRENT_AGENTS=4
MAX_CONCURRENT_BENCHMARKS=2

# Local Ollama models (prefer these over cloud)
DEFAULT_LOCAL_MODEL="qwen3-coder:30b"
REASONING_MODEL="deepseek-r1:7b"
EMBEDDING_MODEL="nomic-embed-text:latest"

# Benchmark limits
MAX_HUMANEVAL_PROBLEMS=50
MAX_BATCH_SIZE=10

# Check available memory
check_memory() {
    local available=$(free -g | awk '/^Mem:/ {print $7}')
    if [ "$available" -lt "$MIN_FREE_GB" ]; then
        echo "WARNING: Only ${available}GB memory available (threshold: ${MIN_FREE_GB}GB)"
        return 1
    fi
    echo "Memory OK: ${available}GB available"
    return 0
}

# Check if process count is safe
check_processes() {
    local python_count=$(pgrep -f "python.*cohezion" | wc -l)
    if [ "$python_count" -gt "$MAX_CONCURRENT_AGENTS" ]; then
        echo "WARNING: $python_count processes running (max: $MAX_CONCURRENT_AGENTS)"
        return 1
    fi
    echo "Process count OK: $python_count running"
    return 0
}

# Get local model (prefer local over cloud)
get_local_model() {
    local model="${1:-$DEFAULT_LOCAL_MODEL}"
    if olist list 2>/dev/null | grep -q "^${model%%:*}"; then
        echo "$model"
    else
        echo "$DEFAULT_LOCAL_MODEL"
    fi
}

# Run benchmark with guardrails
run_benchmark() {
    local benchmark=$1
    local model=${2:-$DEFAULT_LOCAL_MODEL}
    
    if ! check_memory || ! check_processes; then
        echo "Skipping benchmark $benchmark - system resource check failed"
        return 1
    fi
    
    echo "Running $benchmark with model $model"
    # Actual benchmark command would go here
}

# Export for use in Python
export -f check_memory
export -f check_processes
export -f get_local_model
export DEFAULT_LOCAL_MODEL
export MAX_CONCURRENT_AGENTS
export MIN_FREE_GB
