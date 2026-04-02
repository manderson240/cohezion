#!/bin/bash
# Resume Pi-Cohezion Integration Session
# Usage: ./resume-session.sh

echo "=========================================="
echo "Resuming Pi-Cohezion Integration Session"
echo "Date: $(date)"
echo "=========================================="
echo ""

# Check if extension exists
if [ ! -f ".pi/extensions/cohezion-bridge.ts" ]; then
    echo "❌ Extension not found: .pi/extensions/cohezion-bridge.ts"
    exit 1
fi

echo "✓ Extension found"

# Check if skill index exists
if [ ! -f ".pi/integrations/skill_index.json" ]; then
    echo "⚠️  Skill index missing. Rebuilding..."
    python3 .pi/integrations/index_skills.py
fi

echo "✓ Skill index ready ($(jq '.meta.count' .pi/integrations/skill_index.json) skills)"

# Check if vault is accessible
if command -v uv &> /dev/null; then
    echo "✓ uv available"
else
    echo "⚠️  uv not in PATH"
fi

echo ""
echo "=========================================="
echo "Starting pi with extension..."
echo "=========================================="
echo ""

# Start pi with the extension
pi --extension .pi/extensions/cohezion-bridge.ts "$@"
