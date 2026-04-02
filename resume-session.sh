#!/bin/bash
# Resume Cohezion Pi Session with Bridge Extension
# Usage: ./resume-session.sh [additional pi args]

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Cohezion Pi Session Resumer"
echo "=========================================="
echo ""

# Check extension exists
if [ ! -f ".pi/extensions/cohezion-bridge.ts" ]; then
    echo "❌ Extension not found: .pi/extensions/cohezion-bridge.ts"
    exit 1
fi

echo "✓ Cohezion bridge extension found"

# Check skill index exists, rebuild if not
if [ ! -f ".pi/integrations/skill_index.json" ]; then
    echo "⚠️  Skill index missing. Rebuilding..."
    if command -v python3 > /dev/null 2>&1; then
        python3 .pi/integrations/index_skills.py
    else
        echo "❌ python3 not found. Cannot rebuild skill index."
        exit 1
    fi
fi

# Display stats
if [ -f ".pi/integrations/skill_index.json" ]; then
    SKILL_COUNT=$(grep -o '"count": [0-9]*' .pi/integrations/skill_index.json | head -1 | grep -o '[0-9]*' || echo "0")
    echo "✓ Skills indexed: $SKILL_COUNT"
fi

if [ -f ".pi/integrations/anti_pattern_inventory.json" ]; then
    ANTI_PATTERNS=$(grep -o '"anti_patterns"' .pi/integrations/anti_pattern_inventory.json | wc -l)
    if [ "$ANTI_PATTERNS" -gt 0 ]; then
        echo "✓ Anti-pattern inventory available"
    fi
fi

echo ""
echo "Configuration:"
echo "  Extension: .pi/extensions/cohezion-bridge.ts"
echo "  Settings:  .pi/settings.json"
echo ""

# Check if settings.json has the extension
if [ -f ".pi/settings.json" ]; then
    if grep -q "cohezion-bridge.ts" .pi/settings.json; then
        echo "✓ Extension configured in .pi/settings.json"
        echo ""
        echo "Starting pi with settings..."
        pi "$@"
    else
        echo "⚠️  Extension not in settings.json, using command line..."
        echo ""
        pi --extension .pi/extensions/cohezion-bridge.ts "$@"
    fi
else
    echo "⚠️  No settings.json found, using command line..."
    echo ""
    pi --extension .pi/extensions/cohezion-bridge.ts "$@"
fi
