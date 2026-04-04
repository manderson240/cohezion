#!/bin/bash
# Safe Ollama Usage Helper
# Prevents OOM by monitoring memory and stopping models when needed

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Memory threshold (in GB) - leave 60GB for system
MAX_VRAM_GB=60

check_memory() {
    echo -e "${GREEN}=== Memory Status ===${NC}"
    
    # System RAM
    free -h | head -2
    
    # GPU memory (if rocm-smi available)
    if command -v rocm-smi &> /dev/null; then
        echo ""
        echo -e "${GREEN}=== GPU Memory ===${NC}"
        rocm-smi --showmeminfo vram 2>/dev/null || echo "Unable to get GPU memory"
    fi
    
    # Check if Ollama has any models loaded
    echo ""
    echo -e "${GREEN}=== Loaded Models ===${NC}"
    ollama ps 2>/dev/null || echo "No models currently loaded"
}

stop_all_models() {
    echo -e "${YELLOW}Stopping all loaded models...${NC}"
    ollama ps --format json 2>/dev/null | jq -r '.[].name' 2>/dev/null | while read model; do
        if [ -n "$model" ]; then
            echo "Stopping $model..."
            ollama stop "$model" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}All models stopped.${NC}"
}

safe_run() {
    local model="$1"
    shift
    local prompt="$*"
    
    # Check memory first
    local available=$(free -g | awk '/^Mem:/{print $7}')
    
    if [ "$available" -lt 30 ]; then
        echo -e "${RED}WARNING: Low memory ($available GB available)${NC}"
        echo "Consider stopping other models first:"
        ollama ps
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Get model size estimate
    local model_size=""
    case "$model" in
        gemma4:e2b|gemma4-e2b) model_size="~7GB" ;;
        gemma4:e4b|gemma4-e4b|gemma4) model_size="~10GB" ;;
        gemma4:26b|gemma4-26b) model_size="~18GB" ;;
        gemma4:31b|gemma4-31b) model_size="~20GB" ;;
        phi3:mini|phi3) model_size="~2GB" ;;
        *) model_size="unknown" ;;
    esac
    
    echo -e "${GREEN}Running: $model ($model_size)${NC}"
    
    if [ -n "$prompt" ]; then
        ollama run "$model" "$prompt"
    else
        ollama run "$model"
    fi
}

safe_context() {
    local model="$1"
    local context="$2"
    shift 2
    local prompt="$*"
    
    # Check if context is safe for model
    local max_context=32768
    case "$model" in
        gemma4:e2b|gemma4-e2b) max_context=131072 ;;
        gemma4:e4b|gemma4-e4b|gemma4) max_context=65536 ;;
        gemma4:26b|gemma4-26b) max_context=32768 ;;
        gemma4:31b|gemma4-31b) max_context=32768 ;;
        phi3:mini|phi3) max_context=131072 ;;
    esac
    
    if [ "$context" -gt "$max_context" ]; then
        echo -e "${RED}ERROR: Context $context exceeds safe limit for $model (max: $max_context)${NC}"
        echo "This could cause OOM. Use smaller context or different model."
        exit 1
    fi
    
    echo -e "${GREEN}Running: $model with context $context${NC}"
    ollama run "$model" --option num_ctx="$context" "$prompt"
}

# Main
case "${1:-}" in
    check|status)
        check_memory
        ;;
    stop)
        stop_all_models
        ;;
    run)
        shift
        safe_run "$@"
        ;;
    context)
        shift
        safe_context "$@"
        ;;
    models)
        echo -e "${GREEN}=== Available Models ===${NC}"
        echo "Safe models (low memory):"
        echo "  phi3:mini     - 2.2GB   - Fast, good for quick tasks"
        echo "  gemma4:e2b     - 7.2GB   - Balanced, 128K context"
        echo ""
        echo "Medium models:"
        echo "  gemma4:e4b     - 9.6GB   - Default, 64K context safe"
        echo ""
        echo "Large models (use carefully):"
        echo "  gemma4:26b     - 18GB    - MoE efficiency, 32K context"
        echo "  gemma4:31b     - 20GB    - Maximum quality, 32K context"
        echo ""
        echo -e "${YELLOW}Memory Guidelines (128GB unified):${NC}"
        echo "  - Leave 60GB+ free for system"
        echo "  - Only load ONE large model at a time"
        echo "  - Use 'ollama stop <model>' after use"
        ;;
    *)
        echo "Usage: $0 {check|stop|run|context|models}"
        echo ""
        echo "Commands:"
        echo "  check     - Check memory status"
        echo "  stop      - Stop all loaded models"
        echo "  run       - Safely run a model with memory check"
        echo "  context   - Run with specific context size (validates safety)"
        echo "  models    - List available models with memory requirements"
        ;;
esac