#!/bin/bash
# Overnight Autoresearch Runner for Datamesh Optimization
# 
# Usage: ./overnight.sh [max_runs] [checkpoint_interval]
# 
# Runs autoresearch experiments continuously overnight with:
# - Periodic checkpointing
# - Automatic resume on interruption
# - Progress logging
# - Morning report generation
#
# Charter: Transparent operation, resume on failure, no data loss.

set -euo pipefail

# Configuration
SESSION_NAME="datamesh_overnight_$(date +%Y%m%d)"
MAX_RUNS="${1:-50}"
CHECKPOINT_INTERVAL="${2:-5}"
CHECKPOINT_FILE=".autoresearch_checkpoint_${SESSION_NAME}.json"
LOG_FILE="overnight_${SESSION_NAME}.log"
REPORT_FILE="overnight_report_${SESSION_NAME}.md"

# Colors for output (only if terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

# Signal handler for graceful shutdown
cleanup() {
    log "Shutdown requested, saving checkpoint..."
    cat > "$CHECKPOINT_FILE" << EOF
{
  "session_name": "$SESSION_NAME",
  "run_count": $CURRENT_RUN,
  "timestamp": "$(date -Iseconds)",
  "status": "interrupted",
  "git_commit": "$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
}
EOF
    log "Checkpoint saved to $CHECKPOINT_FILE"
    exit 130
}
trap cleanup SIGTERM SIGINT

# Initialize experiment (run once at start)
init_experiment() {
    log "Initializing autoresearch session: $SESSION_NAME"
    log "Target metric: query_latency_ms (lower is better)"
    
    # This initializes the experiment in autoresearch.jsonl
    # In pi, this would be: init_experiment with parameters
}

# Run benchmark and measure
run_benchmark() {
    local run_num=$1
    log "Running benchmark for experiment $run_num..."
    
    # Run benchmark and capture output
    local output
    if output=$(cd /home/mike-anderson/dev/cohezion && uv run python -m cohezion.benchmarks.datamesh_query 2>&1); then
        # Parse METRIC line
        local metric=$(echo "$output" | grep "^METRIC query_latency_ms=" | cut -d= -f2 || echo "999.99")
        local embedding=$(echo "$output" | grep "^METRIC embedding_search_ms=" | cut -d= -f2 || echo "0")
        local cross=$(echo "$output" | grep "^METRIC cross_domain_ms=" | cut -d= -f2 || echo "0")
        
        echo "$metric,$embedding,$cross"
        return 0
    else
        log_error "Benchmark failed: $output"
        return 1
    fi
}

# Generate experiment description based on previous results
generate_hypothesis() {
    local run_num=$1
    
    # Generate hypothesis based on run number patterns
    if (( run_num % 5 == 0 )); then
        echo "Batch query optimization: process multiple queries in parallel"
    elif (( run_num % 5 == 1 )); then
        echo "Embedding cache optimization: LRU cache for 256D vectors"
    elif (( run_num % 5 == 2 )); then
        echo "Query plan optimization: pre-compute common join patterns"
    elif (( run_num % 5 == 3 )); then
        echo "Index optimization: HNSW for vector similarity search"
    else
        echo "Connection pooling: reuse SurrealDB connections"
    fi
}

# Apply optimization (stub for now)
apply_optimization() {
    local run_num=$1
    local hypothesis="$2"
    
    log "Applying optimization: $hypothesis"
    
    # In real implementation, this would modify code and run git commit
    # For now, just simulate
    sleep 1
}

# Main execution
main() {
    log "=" 
    log "OVERNIGHT AUTORESEARCH: Datamesh Graph Optimization"
    log "Session: $SESSION_NAME"
    log "Target: $MAX_RUNS runs, checkpoint every $CHECKPOINT_INTERVAL runs"
    log "=" 
    
    # Initialize
    init_experiment
    
    # Load checkpoint if exists
    local CURRENT_RUN=0
    if [[ -f "$CHECKPOINT_FILE" ]]; then
        CURRENT_RUN=$(jq -r '.run_count // 0' "$CHECKPOINT_FILE" 2>/dev/null || echo 0)
        log "Resuming from checkpoint: run $CURRENT_RUN"
    fi
    
    # Summary tracking
    local BEST_METRIC=99999.99
    local KEEP_COUNT=0
    local DISCARD_COUNT=0
    
    # Main loop
    while (( CURRENT_RUN < MAX_RUNS )); do
        CURRENT_RUN=$((CURRENT_RUN + 1))
        
        log ""
        log "----------------------------------------"
        log "RUN $CURRENT_RUN / $MAX_RUNS"
        log "----------------------------------------"
        
        # Generate hypothesis
        local HYPOTHESIS=$(generate_hypothesis $CURRENT_RUN)
        log "Hypothesis: $HYPOTHESIS"
        
        # Apply optimization
        apply_optimization $CURRENT_RUN "$HYPOTHESIS"
        
        # Run benchmark
        if ! BENCH_RESULT=$(run_benchmark $CURRENT_RUN); then
            log_error "Benchmark failed for run $CURRENT_RUN"
            continue
        fi
        
        # Parse results
        local METRIC=$(echo "$BENCH_RESULT" | cut -d, -f1)
        local EMBEDDING=$(echo "$BENCH_RESULT" | cut -d, -f2)
        local CROSS=$(echo "$BENCH_RESULT" | cut -d, -f3)
        
        # Determine status
        local STATUS
        if (( $(echo "$METRIC < $BEST_METRIC * 0.99" | bc -l) )); then
            STATUS="keep"
            BEST_METRIC=$METRIC
            KEEP_COUNT=$((KEEP_COUNT + 1))
            log "Status: ${GREEN}KEEP${NC} - New best: ${METRIC}ms"
        else
            STATUS="discard"
            DISCARD_COUNT=$((DISCARD_COUNT + 1))
            log "Status: ${YELLOW}DISCARD${NC} - Metric: ${METRIC}ms (best: ${BEST_METRIC}ms)"
        fi
        
        log "Breakdown: query=${METRIC}ms, embedding=${EMBEDDING}ms, cross=${CROSS}ms"
        
        # Checkpoint periodically
        if (( CURRENT_RUN % CHECKPOINT_INTERVAL == 0 )); then
            log "Creating checkpoint..."
            cat > "$CHECKPOINT_FILE" << EOF
{
  "session_name": "$SESSION_NAME",
  "run_count": $CURRENT_RUN,
  "best_metric": $BEST_METRIC,
  "kept": $KEEP_COUNT,
  "discarded": $DISCARD_COUNT,
  "timestamp": "$(date -Iseconds)",
  "status": "running"
}
EOF
        fi
        
        # Brief pause between runs
        sleep 2
    done
    
    # Generate final report
    log ""
    log "Generating final report..."
    
    cat > "$REPORT_FILE" << EOF
# Overnight Autoresearch Report: $SESSION_NAME

**Completed**: $(date)
**Git Commit**: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')

## Summary

| Metric | Value |
|--------|-------|
| Total Runs | $CURRENT_RUN |
| Kept | $KEEP_COUNT |
| Discarded | $DISCARD_COUNT |
| Best Latency | ${BEST_METRIC}ms |
| Improvement | Calculate from baseline |

## Experiments

See detailed log: \`$LOG_FILE\`
Checkpoint: \`$CHECKPOINT_FILE\`

## Key Findings

(TBD - analyze patterns from log)

## Next Steps

1. Review kept experiments for common patterns
2. Apply winning optimizations permanently
3. Update skills with new patterns
EOF

    log "Report saved: $REPORT_FILE"
    log ""
    log "=" 
    log "COMPLETE: $CURRENT_RUN runs ($KEEP_COUNT kept, $DISCARD_COUNT discarded)"
    log "Best metric: ${BEST_METRIC}ms"
    log "=" 
}

# Start from script directory
cd "$(dirname "$0")" || exit 1
main "$@"
