#!/bin/bash
# Submit all three kernels to AMD speedrun

set -e

cd /home/mike-anderson/dev/cohezion/luma_speedrun

echo "=== Submitting MLA ==="
cd amd-mixed-mla
popcorn-cli submit submission.py --mode test --gpu MI355X --leaderboard amd-mixed-mla || echo "MLA failed"
cd ..

echo "=== Submitting MoE ==="
cd amd-moe-mxfp4
cp submission_ultra.py submission.py
popcorn-cli submit submission.py --mode test --gpu MI355X --leaderboard amd-moe-mxfp4 || echo "MoE failed"
cd ..

echo "=== Submitting GEMM ==="
cd amd-mxfp4-mm
cp submission_ultra.py submission.py
popcorn-cli submit submission.py --mode test --gpu MI355X --leaderboard amd-mxfp4-mm || echo "GEMM failed"
cd ..

echo "All submissions complete!"
