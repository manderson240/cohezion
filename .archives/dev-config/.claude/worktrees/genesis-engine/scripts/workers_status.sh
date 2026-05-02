#!/bin/bash
# Consolidated status for all overnight workers

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        OVERNIGHT RESEARCH - ALL WORKERS STATUS                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "⏰ Current: $(date '+%H:%M:%S EST') | Target End: 08:31 EST"
echo ""

# System resources
echo "🖥️  SYSTEM RESOURCES:"
free -h | grep "Mem:" | awk '{printf "   RAM: %s / %s (%s used)\n", $3, $2, $3/$2*100"%"}'
top -bn1 | grep "Cpu(s)" | awk '{printf "   CPU: %.1f%% used\n", 100-$8}'
echo ""

# Main coordinator
echo "📊 MAIN COORDINATOR:"
if pgrep -f "overnight_simple.py" > /dev/null; then
    PID=$(pgrep -f "overnight_simple.py")
    echo "   ✅ Running (PID $PID)"
    ITER=$(grep -c "ITERATION" logs/overnight_live.log 2>/dev/null || echo "0")
    echo "   Iterations: $ITER"
else
    echo "   ❌ NOT RUNNING"
fi
echo ""

# HIHO workers
echo "🔬 HIHO SIMULATION WORKERS:"
for i in 1 2 3 4; do
    if pgrep -f "hiho_worker.py $i" > /dev/null; then
        ITER=$(grep -c "Worker $i" logs/hiho_worker_${i}.log 2>/dev/null || echo "0")
        LAST=$(tail -1 logs/hiho_worker_${i}.log 2>/dev/null | cut -d':' -f2- | head -c 60)
        echo "   Worker $i: ✅ Running ($ITER iters) - $LAST..."
    else
        echo "   Worker $i: ❌ Not running"
    fi
done
echo ""

# Ollama workers
echo "🤖 OLLAMA RESEARCH WORKERS:"
for i in 1 2; do
    if pgrep -f "ollama_worker.py $i" > /dev/null; then
        ITER=$(grep -c "Ollama $i" logs/ollama_worker_${i}.log 2>/dev/null || echo "0")
        echo "   Worker $i: ✅ Running ($ITER queries)"
    else
        echo "   Worker $i: ❌ Not running"
    fi
done
echo ""

# Quick stats
echo "📈 QUICK STATS:"
TOTAL_WORKERS=$(pgrep -f "worker.py" | wc -l)
echo "   Active Workers: $TOTAL_WORKERS / 6"

# Data output
if [ -d "data/overnight" ]; then
    FILES=$(find data/overnight -name "*.json" 2>/dev/null | wc -l)
    echo "   Data Files: $FILES"
fi

echo ""
echo "💡 Logs: tail -f logs/{overnight_live,hiho_worker_*,ollama_worker_*}.log"
