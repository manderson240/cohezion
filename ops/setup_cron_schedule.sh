#!/bin/bash
#
# ASCENDED COHEZION - 24/7 Universe Simulation Scheduler (Fixed)
# Installs cron jobs for automated mission runs
#
# Usage: ./setup_cron_schedule.sh

set -e

COHEZION_ROOT="/home/mike-anderson/dev/cohezion"
LOG_FILE="$COHEZION_ROOT/logs/cron_setup.log"
CRON_FILE="$COHEZION_ROOT/ops/cron/cohezion_schedule"

echo "🌌 ASCENDED COHEZION - Setting up 24/7 Schedule"
echo "==============================================="
echo ""

# Create log directory
mkdir -p "$COHEZION_ROOT/logs"

# Check if cron file exists
if [ ! -f "$CRON_FILE" ]; then
    echo "❌ Cron schedule file not found: $CRON_FILE"
    exit 1
fi

# Show schedule configuration
echo "📅 Schedule Configuration:"
echo "   Track A (Rapid):     Every 6 hours (4h runs)"
echo "   Track B (Balanced):  Every 12 hours (12h runs)"
echo "   Track C (Deep):      Daily at midnight (24h runs)"
echo "   Daily Digest:        4:00 PM"
echo "   Weekly Report:       Sundays 5:00 AM"
echo "   Health Check:        Every hour"
echo ""

# Backup existing crontab
echo "💾 Backing up existing crontab..."
crontab -l > "$COHEZION_ROOT/ops/cron/crontab_backup_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || echo "   No existing crontab"

# Install the cron job
echo "🔧 Installing cron jobs..."
if crontab "$CRON_FILE"; then
    echo "✅ Cron schedule installed!"
else
    echo "❌ Failed to install cron schedule"
    echo "   You may need to install manually:"
    echo "   crontab $CRON_FILE"
    exit 1
fi

echo ""
echo "📋 Current schedule:"
crontab -l | head -40

echo ""
echo "📊 Logs will be saved to:"
echo "   $LOG_FILE"
echo ""
echo "🚀 Cron schedule active!"
echo ""
echo "Next runs:"
echo "  Track C (Deep):      Today at midnight"
echo "  Track B (Balanced):  04:00 and 16:00"
echo "  Track A (Rapid):     06:00, 12:00, 18:00, 00:00"
echo ""
echo "To view all jobs: crontab -l"
echo "To remove:        crontab -r"
