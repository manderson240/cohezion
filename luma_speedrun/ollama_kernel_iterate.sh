#!/bin/bash
# Ollama-driven kernel iteration loop
# Usage: ./ollama_kernel_iterate.sh <kernel> <model>
# Example: ./ollama_kernel_iterate.sh gemm kimi-k2.5:cloud

KERNEL=${1:-gemm}
MODEL=${2:-deepseek-v3.2:cloud}
LUMA_DIR="/home/mike-anderson/dev/cohezion/luma_speedrun"

case $KERNEL in
  gemm)
    LEADERBOARD="amd-mxfp4-mm"
    SUBDIR="amd-mxfp4-mm"
    BEST_FILE="submission_mfma_v1.py"
    TARGET="<13µs geomean (current best: 13.425µs, aiter baseline: 11.5µs)"
    ;;
  moe)
    LEADERBOARD="amd-moe-mxfp4"
    SUBDIR="amd-moe-mxfp4"
    BEST_FILE="submission.py"
    TARGET="<110µs geomean (current best: 154.2µs, rank 1: 70.5µs)"
    ;;
  mla)
    LEADERBOARD="amd-mixed-mla"
    SUBDIR="amd-mixed-mla"
    BEST_FILE="submission.py"
    TARGET="<50µs geomean (current best: 69.7µs, rank 1: 19.5µs)"
    ;;
  *)
    echo "Usage: $0 <gemm|moe|mla> [model]"
    exit 1
    ;;
esac

WORK_DIR="$LUMA_DIR/$SUBDIR"
ITERATION=0

echo "=== Ollama Kernel Optimization ==="
echo "Kernel: $KERNEL ($LEADERBOARD)"
echo "Model: $MODEL"
echo "Target: $TARGET"
echo "Working dir: $WORK_DIR"
echo ""

# Read current best submission
CURRENT_CODE=$(cat "$WORK_DIR/$BEST_FILE")

while true; do
  ITERATION=$((ITERATION + 1))
  echo "--- Iteration $ITERATION ---"

  # Ask Ollama for optimization suggestions
  PROMPT="You are an AMD MI355X GPU kernel optimization expert.

Current $KERNEL submission ($BEST_FILE):
$CURRENT_CODE

Target: $TARGET
GPU: AMD MI355X (gfx950, CDNA4, 304 CUs, 8 XCDs)
Competition: Popcorn CLI, geometric mean across 6-8 benchmark shapes
Error tolerance: GEMM=1%, MoE=5%, MLA=10%

Key constraints:
- aiter API parameters (KSPLIT, block_size) are EXHAUSTED
- load_inline HIP kernels COMPILE AND RUN on the runner
- MFMA 32x32x64 FP4 intrinsic is VERIFIED working
- B_q is standard FP4 packed, B_shuffle is CK-specific format

Propose ONE specific optimization to try. Output ONLY the complete modified submission.py file, nothing else. Focus on:
1. LDS double-buffering for coalesced memory access
2. Multi-tile output (32x128) for A data reuse
3. Vectorized 128-bit global loads
4. XCD-aware scheduling with __builtin_amdgcn_s_setprio
5. Shape-specialized dispatch (different tile sizes for M=4 vs M=256)"

  VARIANT_FILE="$WORK_DIR/submission_ollama_${KERNEL}_iter${ITERATION}.py"

  echo "$PROMPT" | timeout 120 ollama run "$MODEL" 2>/dev/null > "$VARIANT_FILE"

  if [ ! -s "$VARIANT_FILE" ]; then
    echo "Ollama produced empty output, skipping"
    continue
  fi

  # Add popcorn directives if missing
  if ! grep -q "POPCORN" "$VARIANT_FILE"; then
    echo "#!POPCORN leaderboard $LEADERBOARD" > /tmp/popcorn_header.py
    echo "#!POPCORN gpu MI355X" >> /tmp/popcorn_header.py
    echo "" >> /tmp/popcorn_header.py
    cat "$VARIANT_FILE" >> /tmp/popcorn_header.py
    mv /tmp/popcorn_header.py "$VARIANT_FILE"
  fi

  echo "Generated variant: $VARIANT_FILE ($(wc -l < "$VARIANT_FILE") lines)"

  # Test it
  echo "Submitting to test..."
  RESULT=$(cd "$WORK_DIR" && timeout 600 popcorn-cli submit --no-tui --mode test --gpu MI355X --leaderboard "$LEADERBOARD" "$(basename "$VARIANT_FILE")" 2>&1)

  if echo "$RESULT" | grep -q "Testing successful"; then
    echo "PASSED! Submitting to benchmark..."
    BENCH=$(cd "$WORK_DIR" && timeout 600 popcorn-cli submit --no-tui --mode benchmark --gpu MI355X --leaderboard "$LEADERBOARD" "$(basename "$VARIANT_FILE")" 2>&1)

    # Extract timing
    TIMES=$(echo "$BENCH" | grep "⏱" | sed 's/.*⏱ //; s/ ±.*//')
    echo "Benchmark times: $TIMES"

    # Log result
    echo "$(date +%H:%M) iter=$ITERATION file=$(basename "$VARIANT_FILE") times=$TIMES" >> "$WORK_DIR/ollama_results.log"
  else
    echo "FAILED correctness check"
    echo "$(date +%H:%M) iter=$ITERATION file=$(basename "$VARIANT_FILE") FAILED" >> "$WORK_DIR/ollama_results.log"
  fi

  echo ""

  # Rate limit: wait between submissions
  sleep 30
done
