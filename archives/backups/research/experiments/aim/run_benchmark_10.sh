#!/bin/bash
echo "Starting 10-problem benchmark at $(date)"
echo "Model: qwen2-math:1.5b, Timeout: 120s"
uv run python fast_baseline_runner.py \
    --reference input/reference_10.csv \
    --model qwen2-math:1.5b \
    --timeout 120 \
    --output output/fast_baseline_10.json \
    2>&1 | tee output/fast_baseline_10.log
echo "Completed at $(date)"
