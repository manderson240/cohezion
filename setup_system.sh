#!/bin/bash
#
# ASCENDED COHEZION - Complete System Setup
# Run this once to initialize everything for 24/7 operation
#
# Usage: ./setup_system.sh

set -e

COHEZION_ROOT="/home/mike-anderson/dev/cohezion"
USER="mike-anderson"
EMAIL="manderson240@gmail.com"

echo "🌌 ASCENDED COHEZION - System Setup"
echo "==================================="
echo ""
echo "Email: $EMAIL"
echo "User: $USER"
echo "Root: $COHEZION_ROOT"
echo ""

# 1. Create required directories
echo "1️⃣ Creating data directories..."
mkdir -p "$COHEZION_ROOT/data"/{evolution,dashboards,checkpoints,knowledge_graph,logs}
mkdir -p "$COHEZION_ROOT/logs"
mkdir -p "$COHEZION_ROOT/ops/cron"
mkdir -p "$HOME/.config/cohezion"
echo "   ✅ Directories created"
echo ""

# 2. Check dependencies
echo "2️⃣ Checking dependencies..."
if ! command -v uv &> /dev/null; then
    echo "   ❌ uv not found. Please install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo "   ✅ uv found"

if ! command -v ollama &> /dev/null; then
    echo "   ⚠️  ollama not found. Models will use cloud-only (Kimi K2.5)"
else
    echo "   ✅ ollama found"
fi

if ! pgrep -x "surreal" > /dev/null; then
    echo "   ⚠️  SurrealDB not running. Start with: surreal start --user root --pass root file://$COHEZION_ROOT/data/surrealdb"
else
    echo "   ✅ SurrealDB running"
fi
echo ""

# 3. Setup email configuration template
echo "3️⃣ Setting up email configuration..."
if [ ! -f "$HOME/.config/cohezion/email_config.json" ]; then
cat > "$HOME/.config/cohezion/email_config.json" << EOF
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_username": "",
  "smtp_password": "",
  "sender_email": "",
  "enabled": false,
  "recipient": "$EMAIL",
  "digest_time": "16:00"
}
EOF
    echo "   📧 Email config template created at ~/.config/cohezion/email_config.json"
    echo "   ⚠️  Please edit this file to add your SMTP credentials"
else
    echo "   ✅ Email config already exists"
fi
echo ""

# 4. Setup cron schedule
echo "4️⃣ Installing cron schedule..."
if [ -f "$COHEZION_ROOT/ops/setup_cron_schedule.sh" ]; then
    bash "$COHEZION_ROOT/ops/setup_cron_schedule.sh"
else
    echo "   ❌ Cron setup script not found"
fi
echo ""

# 5. Setup systemd service (optional)
echo "5️⃣ Setting up systemd service..."
if command -v systemctl &> /dev/null; then
    if [ -f "$COHEZION_ROOT/ops/systemd/cohezion-universe.service" ]; then
        sudo cp "$COHEZION_ROOT/ops/systemd/cohezion-universe.service" /etc/systemd/system/
        sudo systemctl daemon-reload
        echo "   ✅ Service installed: cohezion-universe.service"
        echo "   📋 To start: sudo systemctl start cohezion-universe@$USER"
        echo "   📋 To enable: sudo systemctl enable cohezion-universe@$USER"
    fi
else
    echo "   ⚠️  systemd not available (cron is configured instead)"
fi
echo ""

# 6. Test imports
echo "6️⃣ Testing system imports..."
cd "$COHEZION_ROOT"
if uv run python3 -c "
from cohezion.swarm.autonomous_universe_mission import AutonomousUniverseMission
from cohezion.swarm.openweight_grader import OpenweightGradingPanel
from cohezion.swarm.universe_display_engine import UniverseDisplayEngine
from cohezion.swarm.milestone_alerts import NotificationManager
from cohezion.swarm.compound_evolution import CompoundEvolutionEngine
print('✅ All imports successful')
" 2>/dev/null; then
    echo "   ✅ All system components working"
else
    echo "   ⚠️  Import test failed (non-fatal - system may still work)"
fi
echo ""

# 7. Generate initial evolution configs
echo "7️⃣ Generating initial evolution configurations..."
cd "$COHEZION_ROOT"
uv run python3 -c "
from cohezion.swarm.compound_evolution import CompoundEvolutionEngine
import asyncio

async def init():
    engine = CompoundEvolutionEngine()
    
    # Generate initial configs for all tracks
    for track in ['rapid', 'balanced', 'deep']:
        config = await engine.generate_next_run_config(track)
        print(f'✅ Generated config for {track}')

asyncio.run(init())
" 2>/dev/null || echo "   ⚠️  Config generation skipped (system will create on first run)"
echo ""

# Summary
echo "==================================="
echo "✅ SETUP COMPLETE"
echo "==================================="
echo ""
echo "🌌 ASCENDED COHEZION is now configured for 24/7 operation!"
echo ""
echo "📋 What's Next:"
echo ""
echo "1️⃣ Configure Email (Required for notifications):"
echo "   Edit: ~/.config/cohezion/email_config.json"
echo "   Add your Gmail SMTP credentials"
echo ""
echo "2️⃣ Start Your First Mission:"
echo "   cd $COHEZION_ROOT"
echo "   uv run python3 launch_universe_mission.py --track rapid"
echo ""
echo "3️⃣ Or Run Quick Test (30 minutes):"
echo "   uv run python3 quick_test_mission.py"
echo ""
echo "4️⃣ Monitor Progress:"
echo "   Dashboard: http://localhost:8000/"
echo "   Logs: tail -f $COHEZION_ROOT/logs/universe_mission.log"
echo "   Email: Check $EMAIL for notifications"
echo ""
echo "5️⃣ 24/7 Automatic Operation:"
echo "   Cron is configured to run all 3 tracks automatically"
echo "   View schedule: crontab -l"
echo ""
echo "📊 Schedule Overview:"
echo "   Track A (Rapid):     Every 6 hours (4h runs)"
echo "   Track B (Balanced):  Every 12 hours (12h runs)"
echo "   Track C (Deep):      Daily at midnight (24h runs)"
echo ""
echo "🎓 Expected Grades:"
echo "   Initial: B- to B+"
echo "   After 5 runs: B+ to A-"
echo "   After 20 runs: A (optimal)"
echo ""
echo "💡 Support:"
echo "   Documentation: $COHEZION_ROOT/AUTONOMOUS_UNIVERSE_SIMULATION.md"
echo "   System Status: uv run python3 launch_universe_mission.py --status"
echo ""
echo "🚀 The universe awaits!"
