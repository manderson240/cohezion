#!/bin/bash
# Live Status Dashboard - Updates every 3 seconds
# Press Ctrl+C to exit

COHEZION_ROOT="/home/mike-anderson/dev/cohezion"
cd "$COHEZION_ROOT"

while true; do
    clear
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║     🌙 COHEZION OVERNIGHT RESEARCH - LIVE STATUS 🌙            ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "⏰ Current Time: $(date '+%H:%M:%S EST')"
    echo "🎯 Mission End:  08:19:00 EST"
    echo ""
    
    # Check if running
    if pgrep -f "overnight_autonomous_run.py" > /dev/null; then
        PID=$(pgrep -f "overnight_autonomous_run.py" | tail -1)
        RUNTIME=$(ps -p $PID -o etime= | xargs)
        echo "✅ Status: RUNNING (PID $PID, Runtime: $RUNTIME)"
    else
        echo "❌ Status: NOT RUNNING"
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 LATEST OUTPUT (Last 15 lines):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -15 logs/overnight_live.log 2>/dev/null | sed 's/^/  /'
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🏥 System Health:"
    echo "  CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
    echo "  RAM: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
    
    # Ollama check
    if systemctl is-active --quiet ollama 2>/dev/null; then
        echo "  Ollama: ✅"
    else
        echo "  Ollama: ⚠️"
    fi
    
    # SurrealDB check
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "  SurrealDB: ✅"
    else
        echo "  SurrealDB: ⚠️"
    fi
    
    echo ""
    echo "💡 Press Ctrl+C to exit • Log: logs/overnight_live.log"
    echo ""
    
    sleep 3
done
