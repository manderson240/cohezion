#!/bin/bash
# Start Ollama proxy for claw-code
# Usage: ./scripts/start-ollama-proxy.sh [port]

PORT=${1:-8082}

# Kill existing proxy
pkill -f "ollama-proxy" 2>/dev/null || true
sleep 1

# Start new proxy
cd "$(dirname "$0")/.."
python3 scripts/ollama-proxy.py $PORT &

echo "Proxy started on port $PORT"
echo ""
echo "To use with claw-code:"
echo "  cd claw-code"
echo "  ANTHROPIC_BASE_URL=http://localhost:$PORT ANTHROPIC_API_KEY=unused ./target/release/claw --model haiku"
echo ""
echo "Available models:"
echo "  haiku  -> phi3:mini"
echo "  sonnet -> gemma4:e4b"
echo "  opus   -> gemma4:26b"