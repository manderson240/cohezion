#!/bin/bash
# Start Ollama Proxy with Memory Safety Checks

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PORT=${1:-8082}

echo -e "${GREEN}=== Ollama Proxy Startup with Safety Checks ===${NC}"

# Check available memory
AVAILABLE_GB=$(free -g | awk '/^Mem:/{print $7}')

if [ "$AVAILABLE_GB" -lt 40 ]; then
    echo -e "${YELLOW}Warning: Low available memory (${AVAILABLE_GB}GB)${NC}"
    echo "Consider stopping other models:"
    ollama ps 2>/dev/null || true
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if proxy is already running
if pgrep -f "ollama-proxy.py" > /dev/null 2>&1; then
    echo -e "${YELLOW}Proxy already running, stopping old instance...${NC}"
    pkill -f "ollama-proxy.py"
    sleep 2
fi

# Check if port is available
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
    echo -e "${RED}Port $PORT is already in use${NC}"
    exit 1
fi

echo -e "${GREEN}Starting proxy on port $PORT...${NC}"

# Set safe Ollama environment
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_KEEP_ALIVE=30m
export OLLAMA_CONTEXT_WINDOW=32768
export OLLAMA_FLASH_ATTENTION=1

# Start proxy
python3 scripts/ollama-proxy.py "$PORT" &
PROXY_PID=$!

# Wait for startup
sleep 2

# Verify proxy is running
if ! kill -0 $PROXY_PID 2>/dev/null; then
    echo -e "${RED}Proxy failed to start${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Proxy Running                                            ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Port:      http://localhost:$PORT                         ║${NC}"
echo -e "${GREEN}║  PID:       $PROXY_PID                                              ║${NC}"
echo -e "${GREEN}║  Memory:    ${AVAILABLE_GB}GB available                            ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Safe Models:                                              ║${NC}"
echo -e "${GREEN}║    --model haiku   (gemma4:e4b, 9.6GB, 32K context)        ║${NC}"
echo -e "${GREEN}║    --model sonnet  (gemma4:26b, 18GB, 32K context)       ║${NC}"
echo -e "${GREEN}║    --model opus    (gemma4:31b, 20GB, 32K context)       ║${NC}"
echo -e "${GREEN}║    --model fast    (phi3:mini, 2.2GB, 128K context)       ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Usage:                                                   ║${NC}"
echo -e "${GREEN}║    cd claw-code                                            ║${NC}"
echo -e "${GREEN}║    ANTHROPIC_BASE_URL=http://localhost:$PORT \\           ║${NC}"
echo -e "${GREEN}║    ANTHROPIC_API_KEY=unused \\                             ║${NC}"
echo -e "${GREEN}║    ./target/release/claw --model haiku                   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Memory Safety: Max 1 model loaded, 32K context limit${NC}"
echo ""

# Test proxy connectivity
if curl -s --max-time 5 "http://localhost:$PORT/v1/messages" \
    -X POST -H "Content-Type: application/json" \
    -d '{"model":"haiku","max_tokens":5,"messages":[{"role":"user","content":"hi"}]}' \
    > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Proxy responding correctly${NC}"
else
    echo -e "${YELLOW}⚡ Proxy started but not yet responding (Ollama may need to warm up)${NC}"
fi

# Show loaded models
echo ""
echo -e "${GREEN}Currently loaded models:${NC}"
ollama ps 2>/dev/null || echo "No models loaded"

echo ""
echo "To stop: pkill -f 'ollama-proxy.py'"