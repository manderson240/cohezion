#!/bin/bash
# Auto-benchmark script for Luma AMD Speedrun
# Runs test → benchmark → logs results WITHOUT needing Claude tokens
#
# Usage: ./auto_benchmark.sh <kernel> <submission_file>
#   kernel: amd-mxfp4-mm | amd-moe-mxfp4 | amd-mixed-mla
#   submission_file: path to submission.py
#
# Example: ./auto_benchmark.sh amd-mixed-mla submission_a7_fastmode.py

set -euo pipefail

KERNEL="${1:?Usage: $0 <kernel> <submission_file>}"
SUBMISSION="${2:?Usage: $0 <kernel> <submission_file>}"
LOG_DIR="$(dirname "$0")"
LOG_FILE="${LOG_DIR}/OPTIMIZATION_LOG.md"
TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M UTC')

echo "=== Luma Auto-Benchmark ==="
echo "Kernel: $KERNEL"
echo "Submission: $SUBMISSION"
echo "Time: $TIMESTAMP"
echo ""

# Step 1: Test
echo "[1/3] Testing correctness..."
cd "${LOG_DIR}/${KERNEL}"
TEST_OUTPUT=$(popcorn-cli submit --no-tui --mode test --gpu MI355X --leaderboard "$KERNEL" "$SUBMISSION" 2>&1)
TEST_RESULT=$(echo "$TEST_OUTPUT" | grep -c "✅" || true)
TEST_FAIL=$(echo "$TEST_OUTPUT" | grep -c "❌" || true)
echo "Tests: ${TEST_RESULT} passed, ${TEST_FAIL} failed"

if [ "$TEST_FAIL" -gt 0 ]; then
    echo "❌ TESTS FAILED — aborting"
    echo "| ${TIMESTAMP} | ${KERNEL} | ${SUBMISSION} | FAIL | FAIL | test failure |" >> "$LOG_FILE"
    exit 1
fi

# Step 2: Benchmark
echo ""
echo "[2/3] Running benchmark..."
BENCH_OUTPUT=$(popcorn-cli submit --no-tui --mode benchmark --gpu MI355X --leaderboard "$KERNEL" "$SUBMISSION" 2>&1)
echo "$BENCH_OUTPUT" | grep "⏱" | head -10

# Extract benchmark times
BENCH_TIMES=$(echo "$BENCH_OUTPUT" | grep "⏱" | sed 's/.*⏱ \([0-9.]*\).*/\1/')
echo ""
echo "Per-shape times (µs):"
echo "$BENCH_TIMES"

# Compute approximate geomean
if command -v python3 &>/dev/null; then
    GEOMEAN=$(echo "$BENCH_TIMES" | python3 -c "
import sys, math
times = [float(l.strip()) for l in sys.stdin if l.strip()]
if times:
    gm = math.exp(sum(math.log(t) for t in times) / len(times))
    print(f'{gm:.1f}')
else:
    print('N/A')
")
    echo "Benchmark geomean: ${GEOMEAN}µs"
else
    GEOMEAN="N/A"
fi

# Step 3: Log results
echo ""
echo "[3/3] Logging results..."
echo "| ${TIMESTAMP} | ${KERNEL} | ${SUBMISSION} | bench=${GEOMEAN}µs | PENDING | benchmark only |" >> "$LOG_FILE"

echo ""
echo "=== Done ==="
echo "To submit to leaderboard (1/hour limit!):"
echo "  cd ${LOG_DIR}/${KERNEL}"
echo "  popcorn-cli submit --no-tui --mode leaderboard --gpu MI355X --leaderboard $KERNEL $SUBMISSION"
echo ""
echo "Current bests: GEMM=13.425µs MoE=154.183µs MLA=69.745µs"
echo "Only submit if benchmark shows CLEAR improvement over these."
