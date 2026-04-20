#!/bin/bash
# EXECUTE AT 23:10 - Rate Limit Clears
# Run this script when rate limit resets

echo "🚀 EXECUTION START - $(date)"
echo "========================================="

BASE_DIR="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun"

# 1. Submit MoE (HIGHEST PRIORITY - 93.7µs potential Rank 1!)
echo ""
echo "[1/4] Submitting MoE - 93.7µs vs 154µs historical..."
cd "$BASE_DIR/amd-moe-mxfp4"
timeout 300 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui 2>&1 | tee /tmp/moe_leaderboard_$(date +%H%M%S).log
echo "✓ MoE submitted"
sleep 10

# 2. Submit GEMM (18.4µs improvement)
echo ""
echo "[2/4] Submitting GEMM - 18.4µs vs 22µs historical..."
cd "$BASE_DIR/amd-mxfp4-mm"
timeout 300 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-mxfp4-mm --no-tui 2>&1 | tee /tmp/gemm_leaderboard_$(date +%H%M%S).log
echo "✓ GEMM submitted"
sleep 10

# 3. Submit MLA (retry)
echo ""
echo "[3/4] Submitting MLA (retry)..."
cd "$BASE_DIR/amd-mixed-mla"
timeout 300 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-mixed-mla --no-tui 2>&1 | tee /tmp/mla_leaderboard_$(date +%H%M%S).log
echo "✓ MLA submitted"
sleep 10

# 4. Test HipKittens MoE
echo ""
echo "[4/4] Testing HipKittens MoE..."
cd "$BASE_DIR/amd-moe-mxfp4"
timeout 300 popcorn-cli submit submission_hipkittens.py --mode test --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui 2>&1 | tee /tmp/hipkittens_test_$(date +%H%M%S).log
if grep -q "success\|✓\|successful" /tmp/hipkittens_test_*.log 2>/dev/null; then
    echo "✓ HipKittens test passed, submitting benchmark..."
    timeout 300 popcorn-cli submit submission_hipkittens.py --mode benchmark --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui 2>&1 | tee /tmp/hipkittens_benchmark_$(date +%H%M%S).log
else
    echo "⚠ HipKittens test failed (check logs)"
fi

echo ""
echo "========================================="
echo "✅ EXECUTION COMPLETE - $(date)"
echo "Check logs in /tmp/ for results"
echo ""
