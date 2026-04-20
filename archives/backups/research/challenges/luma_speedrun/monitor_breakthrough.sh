#!/bin/bash
# Monitor Ralph Loop breakthrough progress

echo "🚀 BREAKTHROUGH MONITOR - Ralph Loop Progress"
echo "================================================"
echo "Started: $(date)"
echo ""

# Check running processes
echo "Active Optimization Agents:"
ps aux | grep -E "ralph_main.py" | grep -v grep | awk '{print "  " $11 " " $12 " " $13 " (CPU: " $3 "%, MEM: " $4 "%, PID: " $2 ")"}'

echo ""
echo "Recent Results:"

# Check logs
for kernel in gemm mla moe; do
    LOG_FILE="$HOME/vaults/cohezion-vault/luma-speedrun/autoresearch/$kernel/ralph_log.jsonl"
    if [ -f "$LOG_FILE" ]; then
        echo "  ${kernel^^}:"
        tail -3 "$LOG_FILE" 2>/dev/null | jq -r '[.cycle, .result_us, .coherence] | @tsv' 2>/dev/null | while read cycle result coherence; do
            echo "    Cycle $cycle: ${result_us}µs (coherence: $coherence)"
        done
    fi
done

echo ""
echo "Vault Status:"
ls -la ~/vaults/cohezion-vault/luma-speedrun/autoresearch/*/ 2>/dev/null | grep -E "ralph_log|state.json" | head -10

echo ""
echo "Press Ctrl+C to exit monitor (agents continue running)"
echo "Check full logs: tail -f /tmp/ralph_*.log"
