#!/bin/bash
set -x
pkill -f "ollama-proxy" 2>/dev/null || true
python3 scripts/ollama-proxy.py &
sleep 3

echo "Checking port..."
ss -tlnp | grep 8082 || echo "NOT LISTENING"

echo "Testing curl..."
curl -s --max-time 15 http://localhost:8082/v1/messages -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"haiku","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'