#!/bin/bash
# Monitor Quality Simulation Progress
# Usage: ./monitor_quality_sim.sh

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          QUALITY SIMULATION v4.0 - PROGRESS MONITOR          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

LOG_FILE="/home/mike-anderson/nvme-simulations/logs/quality_4hr_run.log"
RESULTS_DIR="/home/mike-anderson/nvme-simulations"

# Check if running
PID=$(pgrep -f "quality_simulation_driver.py" | head -1)
if [ -z "$PID" ]; then
    echo "❌ Simulation is not running"
    exit 1
fi

echo "✅ Simulation Status: RUNNING"
echo "   PID: $PID"
echo "   Started: $(ps -o lstart= -p $PID 2>/dev/null || echo 'Unknown')"
echo ""

# Show current phase
echo "📊 CURRENT ACTIVITY:"
tail -20 "$LOG_FILE" 2>/dev/null | grep -E "(PHASE|Progress|Step)" | tail -5
echo ""

# Show resource usage
echo "🖥️  RESOURCE USAGE:"
CPU=$(ps -o %cpu= -p $PID 2>/dev/null || echo "0")
MEM=$(ps -o %mem= -p $PID 2>/dev/null || echo "0")
ELAPSED=$(ps -o etime= -p $PID 2>/dev/null || echo "0:00")
echo "   CPU: ${CPU}%"
echo "   Memory: ${MEM}%"
echo "   Elapsed: $ELAPSED"
echo ""

# Check results
echo "💾 RESULTS:"
if [ -f "$RESULTS_DIR"/quality_results_*.json ]; then
    LATEST=$(ls -t "$RESULTS_DIR"/quality_results_*.json 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        echo "   Latest results: $(basename $LATEST)"
        echo "   Modified: $(stat -c %y "$LATEST" 2>/dev/null | cut -d'.' -f1)"
    fi
else
    echo "   No results file yet (simulation in progress)"
fi
echo ""

# Log tail
echo "📝 RECENT LOG ENTRIES:"
tail -10 "$LOG_FILE" 2>/dev/null
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "Monitor command: tail -f $LOG_FILE"
echo "═══════════════════════════════════════════════════════════════"
