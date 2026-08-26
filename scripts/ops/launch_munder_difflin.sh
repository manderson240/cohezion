#!/usr/bin/env bash
# Launch Munder Difflin Multi-Agent Office Floor for Cohezion
# Integrates Antigravity (agy), Claude Code, OpenCode, and local models.

set -euo pipefail

REPO_DIR="$HOME/dev/cohezion/src/cohezion/skills/munder-difflin-repo"

echo "=========================================================================================="
echo "🏢 LAUNCHING MUNDER DIFFLIN MULTI-AGENT OFFICE FLOOR"
echo "=========================================================================================="
echo "▶ Working Directory: $REPO_DIR"
echo "▶ Agent CLIs Available:"
echo "   • Antigravity (Gemini): $(which agy || echo 'N/A')"
echo "   • Claude Code:          $(which claude || echo 'N/A')"
echo "   • OpenCode:             $(which opencode || echo 'N/A')"
echo "   • Codex:                $(which codex || echo 'N/A')"
echo "=========================================================================================="

export ELECTRON_FLAGS="--no-sandbox --disable-gpu-sandbox"

cd "$REPO_DIR"
npm run dev -- --no-sandbox

