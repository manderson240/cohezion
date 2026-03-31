#!/bin/bash
# Submit variants in rotation

MLA_DIR="/home/mike-anderson/dev/cohezion/luma_speedrun/amd-mixed-mla"
MOE_DIR="/home/mike-anderson/dev/cohezion/luma_speedrun/amd-moe-mxfp4"
GEMM_DIR="/home/mike-anderson/dev/cohezion/luma_speedrun/amd-mxfp4-mm"

echo "=== Rotation Submitter ==="
echo "Started at: $(date)"

# MLA variants
for f in submission_aggressive.py submission_no_cache.py submission_hyper.py; do
    if [ -f "$MLA_DIR/$f" ]; then
        echo "Submitting MLA: $f"
        cp "$MLA_DIR/$f" "$MLA_DIR/submission.py"
        timeout 180 popcorn-cli submit "$MLA_DIR/submission.py" --mode test --gpu MI355X --leaderboard amd-mixed-mla --no-tui 2>&1 | tail -5
        echo "Waiting 600s..."
        sleep 600
    fi
done

# MoE variants
for f in submission_minimal.py submission_ultra.py submission.py; do
    if [ -f "$MOE_DIR/$f" ]; then
        echo "Submitting MoE: $f"
        cp "$MOE_DIR/$f" "$MOE_DIR/submission.py"
        timeout 180 popcorn-cli submit "$MOE_DIR/submission.py" --mode test --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui 2>&1 | tail -5
        echo "Waiting 600s..."
        sleep 600
    fi
done

# GEMM variants
for f in submission.py submission_inline.py; do
    if [ -f "$GEMM_DIR/$f" ]; then
        echo "Submitting GEMM: $f"
        cp "$GEMM_DIR/$f" "$GEMM_DIR/submission.py"
        timeout 180 popcorn-cli submit "$GEMM_DIR/submission.py" --mode test --gpu MI355X --leaderboard amd-mxfp4-mm --no-tui 2>&1 | tail -5
        echo "Waiting 600s..."
        sleep 600
    fi
done

echo "Complete: $(date)"
