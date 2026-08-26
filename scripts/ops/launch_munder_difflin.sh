#!/usr/bin/env bash
# Launch Munder Difflin Multi-Agent Office Floor for Cohezion
# Fully configured for 100% Local Inference via Lemonade (:13305) & Ollama (:11434)

set -euo pipefail

REPO_DIR="$HOME/dev/cohezion/src/cohezion/skills/munder-difflin-repo"

echo "=========================================================================================="
echo "🏢 LAUNCHING MUNDER DIFFLIN LOCAL MULTI-AGENT FLOOR"
echo "=========================================================================================="
echo "▶ Working Directory: $REPO_DIR"
echo "▶ Local Inference Endpoints:"
echo "   • Lemonade OmniRouter (NPU/iGPU/CPU): http://127.0.0.1:13305/v1"
echo "   • Ollama Daemon:                      http://127.0.0.1:11434"
echo "▶ Local Agent Roster:"
echo "   • OpenCode CLI (Local Engine):        $(which opencode || echo 'N/A')"
echo "   • Antigravity / agy (Local Gemini):   $(which agy || echo 'N/A')"
echo "   • Default Orchestrator (Michael):     OpenCode -> local/qwen3.6-moe-35b-a3b-FLM"
echo "   • Default Worker:                     OpenCode -> local/Qwen3-Coder-30B"
echo "=========================================================================================="

export ELECTRON_FLAGS="--no-sandbox --disable-gpu-sandbox"

cd "$REPO_DIR"
npm run dev
