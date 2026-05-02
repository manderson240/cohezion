#!/bin/bash
# Luma AMD Speedrun - Research Submission Script
# Submits untapped optimization kernels when rate limit allows

cd /home/mike-anderson/dev/cohezion/luma_speedrun

echo "=== Luma AMD Speedrun - Research Submission Script ==="
echo "Date: $(date)"
echo ""

# Check rate limit
check_rate_limit() {
    # Try a dummy submission to check rate limit
    result=$(popcorn-cli submit --mode test --leaderboard amd-moe-mxfp4 --gpu MI355X /dev/null 2>&1 | head -1)
    if echo "$result" | grep -q "Rate limit"; then
        echo "Rate limit active. Waiting..."
        return 1
    fi
    return 0
}

# Test if rate limit is cleared
echo "Checking rate limit status..."
if ! check_rate_limit; then
    echo "Rate limit still active. Cannot submit yet."
    echo "Try again in ~10 minutes."
    exit 1
fi

echo "Rate limit cleared! Proceeding with submissions..."
echo ""

# ──────────────────────────────────────────────────────────────────────
# TIER 1: Research Kernels (Untapped Optimizations)
# ──────────────────────────────────────────────────────────────────────

echo "=== TIER 1: Research Kernels ==="
echo ""

# 1. MoE Activation Scales (untapped a1/a2_scale)
echo "Submitting: MoE Activation Scales Research..."
popcorn-cli submit --mode test --leaderboard amd-moe-mxfp4 --gpu MI355X \
    amd-moe-mxfp4/submission_research_activation_scales.py --no-tui 2>&1 | tail -20
echo ""
sleep 5

# 2. GEMM Bias Fusion (untapped alpha/beta)
echo "Submitting: GEMM Bias Fusion Research..."
popcorn-cli submit --mode test --leaderboard amd-mxfp4-mm --gpu MI355X \
    amd-mxfp4-mm/submission_research_bias_fusion.py --no-tui 2>&1 | tail -20
echo ""
sleep 5

# 3. MLA max_split tuning
echo "Submitting: MLA max_split Research..."
popcorn-cli submit --mode test --leaderboard amd-mixed-mla --gpu MI355X \
    amd-mixed-mla/submission_research_maxsplit.py --no-tui 2>&1 | tail -20
echo ""
sleep 5

# ──────────────────────────────────────────────────────────────────────
# TIER 2: Master Kernels (All Proven Optimizations)
# ──────────────────────────────────────────────────────────────────────

echo "=== TIER 2: Master Kernels ==="
echo ""

# 4. MoE Master (all proven opts + dispatch_policy=1)
echo "Submitting: MoE Master (all proven)..."
popcorn-cli submit --mode test --leaderboard amd-moe-mxfp4 --gpu MI355X \
    amd-moe-mxfp4/submission_master_all_proven.py --no-tui 2>&1 | tail -20
echo ""
sleep 5

# ──────────────────────────────────────────────────────────────────────
# TIER 3: Benchmark Mode (if tests pass)
# ──────────────────────────────────────────────────────────────────────

echo "=== TIER 3: Benchmark Mode ==="
echo ""
read -p "Run benchmark mode on proven kernels? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Benchmarking MoE Master..."
    popcorn-cli submit --mode benchmark --leaderboard amd-moe-mxfp4 --gpu MI355X \
        amd-moe-mxfp4/submission_master_all_proven.py --no-tui 2>&1 | tail -40
fi

# ──────────────────────────────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────────────────────────────

echo ""
echo "=== Submission Summary ==="
echo "Check status with:"
echo "  popcorn-cli submissions list --leaderboard amd-moe-mxfp4"
echo "  popcorn-cli submissions list --leaderboard amd-mxfp4-mm"
echo "  popcorn-cli submissions list --leaderboard amd-mixed-mla"
echo ""
echo "Research kernels submitted:"
echo "  1. MoE Activation Scales (untapped a1/a2_scale)"
echo "  2. GEMM Bias Fusion (untapped alpha/beta)"
echo "  3. MLA max_split tuning (untapped parameter)"
echo "  4. MoE Master (all proven optimizations)"
echo ""
echo "Next steps:"
echo "  - Wait for test results"
echo "  - If passing, submit to leaderboard"
echo "  - Compare performance vs baseline"
