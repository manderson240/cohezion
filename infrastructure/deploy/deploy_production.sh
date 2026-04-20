#!/bin/bash
# Production Deployment Script for TokenEfficientSquad
# Sets up daily cron scheduling and validates system

echo "=============================================="
echo "TokenEfficientSquad Production Deployment"
echo "=============================================="
echo ""

# Check if we're in the right directory
if [ ! -f "production_scheduler.py" ]; then
    echo "Error: production_scheduler.py not found"
    echo "Please run from project root: /home/mike-anderson/dev/cohezion"
    exit 1
fi

# Create vault directories
mkdir -p data/vault/production/logs
echo "✅ Vault directories created"

# Run validation test first
echo ""
echo "Running validation test..."
uv run python3 production_scheduler.py --mode validate > data/vault/production/logs/validation_$(date +%Y%m%d_%H%M%S).log 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Validation passed"
else
    echo "⚠️  Validation issues detected, check logs"
fi

# Set up cron jobs
echo ""
echo "Setting up cron jobs..."

# Create crontab entries
CRON_FULL="0 9 * * * cd $(pwd) \u0026\u0026 uv run python3 production_scheduler.py --mode full \u003e\u003e data/vault/production/logs/daily_$(date +\%Y\%m).log 2\u003e\u00261"
CRON_QUICK="0 */6 * * * cd $(pwd) \u0026\u0026 uv run python3 production_scheduler.py --mode quick \u003e\u003e data/vault/production/logs/quick_$(date +\%Y\%m).log 2\u003e\u00261"

# Backup existing crontab
crontab -l \u003e data/vault/production/logs/crontab.backup.$(date +%Y%m%d) 2\u003e/dev/null || echo "No existing crontab"

# Add to crontab
echo "$CRON_FULL" | crontab -
echo "$CRON_QUICK" | crontab -

echo "✅ Cron jobs installed"
echo ""
echo "Schedule:"
echo "  Full optimization: Daily at 9:00 AM"
echo "  Quick check: Every 6 hours"
echo ""

# Create monitoring script
cat \u003e monitor_production.sh \u003c\u003c 'EOF'
#!/bin/bash
# Monitor production runs

echo "Recent Production Runs:"
echo "========================"
ls -lt data/vault/production/result_*.json 2\u003e/dev/null | head -5

echo ""
echo "Latest Report Summary:"
echo "====================="
if [ -f "data/vault/production/production_report.json" ]; then
    cat data/vault/production/production_report.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
summary = data.get('summary', {})
print(f\"Skills: {summary.get('skills', 0)}\")
print(f\"Optimized: {summary.get('optimized', 0)}\")
print(f\"Efficiency: {summary.get('efficiency', 0)*100:.1f}%\")
print(f\"Total Tokens: {summary.get('total_tokens', 0):,}\")
"
fi

echo ""
echo "Disk Usage:"
echo "==========="
du -sh data/vault/production/ 2\u003e/dev/null
EOF

chmod +x monitor_production.sh
echo "✅ Monitoring script created: monitor_production.sh"

echo ""
echo "=============================================="
echo "Deployment Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "  1. Review validation logs in data/vault/production/logs/"
echo "  2. Run: ./monitor_production.sh"
echo "  3. Check cron: crontab -l"
echo ""
echo "TokenEfficientSquad is now in production mode"
