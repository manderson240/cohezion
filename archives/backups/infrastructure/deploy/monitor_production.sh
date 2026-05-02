#!/bin/bash
# Monitor production runs

echo "Recent Production Runs:"
echo "========================"
ls -lt data/vault/production/result_*.json 2>/dev/null | head -5

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
du -sh data/vault/production/ 2>/dev/null
