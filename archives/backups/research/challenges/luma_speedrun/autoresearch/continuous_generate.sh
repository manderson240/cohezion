#!/bin/bash
# 🚀 Continuous Kernel Generation Loop
# Runs until 7 AM EST, generating variants with Ollama

LUMA_DIR="/home/mike-anderson/dev/cohezion/luma_speedrun"
ITERATION=0
MAX_ITERATIONS=20  # Prevent infinite loop

# Ollama models to rotate through
MODELS=("deepseek-v3.2:cloud" "kimi-k2.5:cloud" "qwen3.5:cloud" "gemma4:cloud")

# Kernels to generate
KERNELS=("moe" "mla" "gemm")

echo "=== Continuous Kernel Generation ==="
echo "Target: Generate until 7 AM EST"
echo "Models: ${MODELS[@]}"
echo "Kernels: ${KERNELS[@]}"
echo ""

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))
    MODEL=${MODELS[$((ITERATION % ${#MODELS[@]}))]}
    KERNEL=${KERNELS[$((ITERATION % ${#KERNELS[@]}))]}
    
    echo "--- Iteration $ITERATION ---"
    echo "Model: $MODEL | Kernel: $KERNEL"
    
    # Generate variant
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    OUTFILE="$LUMA_DIR/autoresearch/generated/variant_${KERNEL}_${ITERATION}_${TIMESTAMP}.py"
    
    mkdir -p "$LUMA_DIR/autoresearch/generated"
    
    # Ollama prompt
    PROMPT="Generate a novel $KERNEL kernel variant for AMD MI355X. Target: Top 20 leaderboard. Output ONLY submission.py starting with #!POPCORN leaderboard"
    
    # Run Ollama (with timeout)
    timeout 180 ollama run "$MODEL" "$PROMPT" 2>/dev/null > "$OUTFILE" || echo "Timeout/failed"
    
    if [ -s "$OUTFILE" ]; then
        echo "Generated: $OUTFILE ($(wc -l < $OUTFILE) lines)"
    else
        rm -f "$OUTFILE"
        echo "Skipped (empty)"
    fi
    
    # Rate limit
    sleep 30
done

echo "=== Generation Complete ==="
