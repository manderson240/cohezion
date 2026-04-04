#!/bin/bash
# START_OVERNIGHT_WITH_GEMMA4.sh - Launch overnight system with Ollama support

echo "🚀 STARTING OVERNIGHT SYSTEM WITH GEMMA4 OFFLOAD"
echo "Time: $(date)"
echo ""

# Check Ollama
echo "Checking Ollama..."
if command -v ollama > /dev/null 2>&1; then
    echo "✅ Ollama available"
    ollama ps 2>/dev/null | head -5 || echo "  (no running models)"
else
    echo "⚠️  Ollama not installed"
    echo "   Install: curl -fsSL https://ollama.com/install.sh | sh"
    echo ""
fi

# Start main overnight system
echo ""
echo "Starting production overnight system..."

WORKTREE="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
cd "$WORKTREE"

# Create the overnight runner
cat > running_overnight.sh <> 'INNEREOF'
#!/bin/bash
LOG="/tmp/overnight_$(date +%Y%m%d).log"
echo "[$(date)] Starting round..." >> "$LOG"

# Submit all three kernels
cd "$WORKTREE/luma_speedrun/amd-mixed-mla"
timeout 300 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-mixed-mla --no-tui >> "$LOG" 2>&1 &
sleep 60

cd "$WORKTREE/luma_speedrun/amd-moe-mxfp4"
timeout 300 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui >> "$LOG" 2>&1 &
sleep 60

cd "$WORKTREE/luma_speedrun/amd-mxfp4-mm"
timeout 300 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-mxfp4-mm --no-tui >> "$LOG" 2>&1 &

sleep 3000
echo "[$(date)] Round complete" >> "$LOG"
INNEREOF
chmod +x running_overnight.sh

# Run first round immediately
echo "Launching first round..."
bash running_overnight.sh &

# Schedule every hour using cron-like loop
echo "Scheduling hourly runs..."
while true; do
    sleep 3600
    echo "[$(date)] Starting scheduled round" | tee -a /tmp/overnight_schedule.log
    bash running_overnight.sh &
done &

SCHEDULER_PID=$!
echo "✅ Scheduler PID: $SCHEDULER_PID"
echo ""
echo "MONITORING:"
echo "  tail -f /tmp/overnight_$(date +%Y%m%d).log"
echo "  ps aux | grep overnight"
echo ""
echo "System will run until deadline (Apr 6, 2026)"
echo "Gemma4 will assist with log analysis when available"
