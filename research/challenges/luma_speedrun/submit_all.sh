#!/bin/bash
# Submit all three kernels for testing — run after rate limit clears
set -e

echo "=== GEMM: LDS-tiled MFMA ==="
cp amd-mxfp4-mm/submission_lds_mfma.py amd-mxfp4-mm/submission.py
popcorn-cli submit --no-tui --mode benchmark --gpu MI355X --leaderboard amd-mxfp4-mm amd-mxfp4-mm/submission.py 2>&1 | grep -E "(⏱|µs|Benchmark|error)"

echo ""
echo "=== MoE: fmoe probe ==="
cp amd-moe-mxfp4/submission_fmoe_probe.py amd-moe-mxfp4/submission.py
popcorn-cli submit --no-tui --mode test --gpu MI355X --leaderboard amd-moe-mxfp4 amd-moe-mxfp4/submission.py 2>&1 | grep -E "(✅|❌|MOE|error)"

echo ""
echo "=== MLA: hybrid v2 ==="
cp amd-mixed-mla/submission_hybrid_v2.py amd-mixed-mla/submission.py
popcorn-cli submit --no-tui --mode test --gpu MI355X --leaderboard amd-mixed-mla amd-mixed-mla/submission.py 2>&1 | grep -E "(✅|❌|error)"
