#!/bin/bash
set -x

# Kill old proxy
pkill -f "ollama-proxy" 2>/dev/null || true
sleep 1

# Start proxy
python3 scripts/ollama-proxy.py &
sleep 3

# Verify proxy is up
echo "Testing proxy with curl..."
curl -s --max-time 15 http://localhost:8082/v1/messages -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"haiku","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}' 
echo ""
echo "Proxy working!"

# Now test claw-code
echo ""
echo "Testing claw-code..."
cd claw-code
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY=unused timeout 30 ./target/release/claw --model haiku prompt "say hello"