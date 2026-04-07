#!/bin/bash
# Test script for the Ollama proxy

echo "=== Testing Ollama Proxy ==="
echo ""

# Ensure proxy is running
if ! pgrep -f "ollama-proxy.py" > /dev/null; then
    echo "Starting proxy..."
    ./scripts/start-ollama-proxy.sh &
    sleep 3
fi

# Test 1: Direct Ollama (baseline)
echo "Test 1: Direct Ollama call (baseline)"
time timeout 30 ollama run gemma4:e4b "What is 2+2? Answer with just the number." 2>&1 | tail -2
echo ""

# Wait for model to stay loaded
sleep 2

# Test 2: Via Proxy 
echo "Test 2: Via Proxy to Ollama"
time curl -s --max-time 60 http://localhost:8082/v1/messages \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"haiku","max_tokens":20,"messages":[{"role":"user","content":"What is 2+2? Answer with just the number."}]}' 2>&1 | jq -r '.content[0].text // .error // .'
echo ""

# Check memory
echo "=== Memory after tests ==="
free -h | awk '/^Mem:/{print "Available: " $7 " (was 76GB)"}'
ollama ps