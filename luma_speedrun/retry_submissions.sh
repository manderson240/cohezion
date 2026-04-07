#!/bin/bash
# Retry kernel submissions — run when runner queue clears
# Deadline: 2026-04-07 07:59 UTC

echo "=== $(date -u) === Retrying submissions..."

cd /home/mike-anderson/dev/cohezion/luma_speedrun

# GEMM: test new custom kernels
echo "--- GEMM tile32x128 ---"
popcorn submit amd-mxfp4-mm/submission_tile32x128.py --mode test --leaderboard amd-mxfp4-mm --no-tui 2>&1 | tail -5

echo "--- GEMM shape_dispatch ---"
popcorn submit amd-mxfp4-mm/submission_shape_dispatch.py --mode test --leaderboard amd-mxfp4-mm --no-tui 2>&1 | tail -5

echo "--- GEMM smalltile ---"
popcorn submit amd-mxfp4-mm/submission_smalltile_gemm.py --mode test --leaderboard amd-mxfp4-mm --no-tui 2>&1 | tail -5

# MLA: test aggressive splits
echo "--- MLA aggressive_splits ---"
popcorn submit amd-mixed-mla/submission_aggressive_splits.py --mode test --leaderboard amd-mixed-mla --no-tui 2>&1 | tail -5

echo "=== $(date -u) === Done"
