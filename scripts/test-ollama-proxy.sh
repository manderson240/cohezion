#!/bin/bash
# Test the Ollama Proxy - Run this manually in a terminal

# Kill any existing proxy
pkill -f "ollama-proxy" 2>/dev/null

# Start fresh
echo "Starting proxy..."
python3 scripts/ollama-proxy.py &
sleep 3

# Test with fast model (phi3:mini)
echo ""
echo "=== Test 1: Fast Model (phi3:mini) ==="
curl --max-time 60 http://localhost:8082/v1/messages \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"fast","max_tokens":50,"messages":[{"role":"user","content":"What is 2+2?"}]}'
echo ""

# Test with cloud model
echo ""
echo "=== Test 2: Cloud Model (gemma4:31b-cloud) ==="
curl --max-time 60 http://localhost:8082/v1/messages \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"cloud","max_tokens":50,"messages":[{"role":"user","content":"Say hello"}]}'
echo ""

# Test with local gemma4
echo ""
echo "=== Test 3: Local Model (gemma4:e4b) ==="
curl --max-time 60 http://localhost:8082/v1/messages \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"haiku","max_tokens":50,"messages":[{"role":"user","content":"Hello"}]}'
echo ""

echo ""
echo "Tests complete. Check memory:"
free -h | head -2
ollama ps