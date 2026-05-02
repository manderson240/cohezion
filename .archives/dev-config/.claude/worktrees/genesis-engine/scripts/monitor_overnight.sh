#!/bin/bash
# Monitor the overnight autonomous research sprint
# Usage: ./monitor_overnight.sh

COHEZION_ROOT="/home/mike-anderson/dev/cohezion"
cd "$COHEZION_ROOT"

echo "🌙 COHEZION OVERNIGHT RESEARCH MONITOR"
echo "======================================"
echo ""

# Check if process is running
if pgrep -f "overnight_autonomous_run.py" > /dev/null; then
    PID=$(pgrep -f "overnight_autonomous_run.py")
    echo "✅ Overnight process RUNNING (PID: $PID)"
    
    # CPU/RAM usage
    ps -p $PID -o %cpu,%mem,cmd | tail -1
    echo ""
else
    echo "❌ Overnight process NOT RUNNING"
    echo ""
fi

# Latest log file
LATEST_LOG=$(ls -t logs/overnight_*.log 2>/dev/null | head -1)

if [ -n "$LATEST_LOG" ]; then
    echo "📋 Latest Log: $LATEST_LOG"
    echo "Last 20 lines:"
    echo "----------------------------------------"
    tail -20 "$LATEST_LOG"
    echo "----------------------------------------"
else
    echo "⚠️  No log files found"
fi

echo ""
echo "🔍 Quick Stats:"
# Check for discoveries
if [ -f "data/overnight/discoveries.json" ]; then
    echo "  Discoveries: $(jq '. | length' data/overnight/discoveries.json 2>/dev/null || echo 'N/A')"
fi

# Check for skills
SKILL_COUNT=$(ls -1 src/cohezion/skills/*_PRIME.md 2>/dev/null | wc -l)
echo "  Total Skills: $SKILL_COUNT"

# Check system health
echo ""
echo "🏥 System Health:"
echo "  CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "  RAM: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"

# Ollama status
if systemctl is-active --quiet ollama; then
    echo "  Ollama: ✅ Active"
else
    echo "  Ollama: ❌ Inactive"
fi

# SurrealDB status  
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  SurrealDB: ✅ Responsive"
else
    echo "  SurrealDB: ❌ Not Responding"
fi

echo ""
echo "💡 Commands:"
echo "  Follow logs:  tail -f $LATEST_LOG"
echo "  Stop process: kill $PID"
echo "  Restart:      nohup python3 scripts/overnight_autonomous_run.py > logs/overnight_\$(date +%Y%m%d_%H%M).log 2>&1 &"
