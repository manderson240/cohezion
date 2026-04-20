#!/bin/bash
# AGENT_DEPLOYMENT.sh - Deploy specialist agents for YOLO phase
# Run from /home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun

set -e

echo "🔥🔥🔥 DEPLOYING SPECIALIST AGENTS FOR LUMA BREAKTHROUGH 🔥🔥🔥"
echo "Time: $(date)"
echo "Deadline: April 6, 2026 11:59 PM PST"
echo ""

# Ensure we're in the right directory
cd /home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun

echo "════════════════════════════════════════════════════"
echo "  DEPLOYING 3 SPECIALIST AGENTS"
echo "════════════════════════════════════════════════════"
echo ""

# Agent 1: GEMM Specialist
echo "🚀 [Agent 1/3] GEMM SPECIALIST"
echo "    Focus: AMD MXFP4-MM leaderboard"
echo "    Target: 7.651μs"
echo "    Strategy: 8-wave ping-pong, fused_gemm, blockscale tuning"
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun/amd-mxfp4-mm
timeout 180 popcorn-cli submit submission.py --mode benchmark --gpu MI355X --leaderboard amd-mxfp4-mm --no-tui 2>&1 | tee /tmp/agent_gemm.log &
echo "    PID: $!"
echo ""

# Agent 2: MoE Specialist
echo "🚀 [Agent 2/3] MoE SPECIALIST"
echo "    Focus: AMD MOE-MXFP4 leaderboard"
echo "    Target: 70.47μs"
echo "    Strategy: Direct CK dispatch, block size tuning"
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun/amd-moe-mxfp4
timeout 180 popcorn-cli submit submission.py --mode benchmark --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui 2>&1 | tee /tmp/agent_moe.log &
echo "    PID: $!"
echo ""

# Agent 3: MLA Specialist
echo "🚀 [Agent 3/3] MLA SPECIALIST"
echo "    Focus: AMD MIXED-MLA leaderboard"
echo "    Target: 19.484μs"
echo "    Strategy: SDPA fusion, custom kernel"
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun/amd-mixed-mla
timeout 180 popcorn-cli submit submission_fixed.py --mode benchmark --gpu MI355X --leaderboard amd-mixed-mla --no-tui 2>&1 | tee /tmp/agent_mla.log &
echo "    PID: $!"
echo ""

echo "════════════════════════════════════════════════════"
echo "  ALL AGENTS DEPLOYED"
echo "════════════════════════════════════════════════════"
echo ""
echo "Active processes: $(ps aux | grep popcorn-cli | grep -v grep | wc -l)"
echo "Monitoring logs:"
echo "  - GEMM: tail -f /tmp/agent_gemm.log"
echo "  - MoE:  tail -f /tmp/agent_moe.log"
echo "  - MLA:  tail -f /tmp/agent_mla.log"
echo ""
echo "Status check in 60 seconds..."
sleep 60
echo ""
echo "=== STATUS CHECK ==="
echo "Active processes: $(ps aux | grep popcorn-cli | grep -v grep | wc -l)"
echo ""
echo "Latest submissions:"
timeout 10 popcorn-cli submissions list --leaderboard amd-mxfp4-mm 2>/dev/null | head -3 | tail -1
timeout 10 popcorn-cli submissions list --leaderboard amd-moe-mxfp4 2>/dev/null | head -3 | tail -1
timeout 10 popcorn-cli submissions list --leaderboard amd-mixed-mla 2>/dev/null | head -3 | tail -1

echo ""
echo "✅ Agent deployment complete"
echo "Next: Monitor results and iterate"
