#!/bin/bash
# Continuous monitoring script - runs every 5 minutes

echo "=== $(date) ===" >> /tmp/monitor.log

# Check for new submissions
echo "MLA:" >> /tmp/monitor.log
timeout 10 popcorn-cli submissions list --leaderboard amd-mixed-mla 2>&1 | head -3 >> /tmp/monitor.log

echo "MoE:" >> /tmp/monitor.log
timeout 10 popcorn-cli submissions list --leaderboard amd-moe-mxfp4 2>&1 | head -3 >> /tmp/monitor.log

echo "GEMM:" >> /tmp/monitor.log
timeout 10 popcorn-cli submissions list --leaderboard amd-mxfp4-mm 2>&1 | head -3 >> /tmp/monitor.log

echo "" >> /tmp/monitor.log
