#!/bin/bash
# AIMO Production Submission Runner

echo "========================================"
echo "AIMO Production Submission"
echo "========================================"
echo "Start: $(date)"
echo "========================================"

# Create output directory
mkdir -p output

# Run submission driver
python aim_submission_driver.py \
    --test-csv input/test.csv \
    --output output/submission.parquet \
    --cache-size 512 \
    2>&1 | tee output/submission.log

echo ""
echo "========================================"
echo "Submission Complete"
echo "Output: output/submission.parquet"
echo "End: $(date)"
echo "========================================"
