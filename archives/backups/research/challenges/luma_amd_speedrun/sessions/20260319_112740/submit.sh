#!/bin/bash
# Popcorn CLI Submission Script
# Submit challengers to MI355X via popcorn-cli

set -e

SESSION_DIR="/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/sessions/20260319_112740"
KERNEL_DIR="/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "GPU MODE Speedrun — Popcorn Submission"
echo "=========================================="
echo ""

# Check popcorn-cli is available
if ! command -v popcorn &> /dev/null; then
    echo -e "${RED}ERROR: popcorn-cli not found${NC}"
    echo "Install: https://github.com/gpu-mode/popcorn-cli"
    exit 1
fi

# Check authentication
echo "Checking popcorn authentication..."
if ! popcorn auth status &> /dev/null; then
    echo -e "${YELLOW}WARNING: Not authenticated. Run 'popcorn auth login' first.${NC}"
fi

echo ""
echo "Available kernels:"
echo "  1. MLA (amd-mixed-mla)"
echo "  2. GEMM (amd-mxfp4-mm)"
echo "  3. MoE (amd-moe-mxfp4)"
echo ""

read -p "Select kernel [1-3] or 'all': " choice

case $choice in
    1|"MLA"|"mla")
        KERNELS=("mla")
        ;;
    2|"GEMM"|"gemm")
        KERNELS=("gemm")
        ;;
    3|"MoE"|"moe")
        KERNELS=("moe")
        ;;
    "all"|"All"|"ALL")
        KERNELS=("mla" "gemm" "moe")
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

for kernel in "${KERNELS[@]}"; do
    echo ""
    echo -e "${GREEN}=== Submitting ${kernel} ===${NC}"
    
    LEADERBOARD=""
    SRC_FILE=""
    
    case $kernel in
        mla)
            LEADERBOARD="amd-mixed-mla"
            SRC_FILE="${SESSION_DIR}/challengers/mla/"
            ;;
        gemm)
            LEADERBOARD="amd-mxfp4-mm"
            SRC_FILE="${SESSION_DIR}/challengers/gemm/"
            ;;
        moe)
            LEADERBOARD="amd-moe-mxfp4"
            SRC_FILE="${SESSION_DIR}/challengers/moe/"
            ;;
    esac
    
    echo "Leaderboard: $LEADERBOARD"
    echo "Source: $SRC_FILE"
    
    # List available variants
    echo ""
    echo "Available variants:"
    ls -1 "$SRC_FILE"*.py 2>/dev/null || echo "  No variants found"
    
    echo ""
    read -p "Submit all variants? [y/N]: " confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        for py_file in "$SRC_FILE"*.py; do
            if [[ -f "$py_file" ]]; then
                echo ""
                echo "Submitting: $(basename $py_file)"
                echo "Command: popcorn submit --mode test --gpu MI355X --leaderboard $LEADERBOARD $py_file"
                
                # For now, just print the command
                # Uncomment for actual submission:
                # popcorn submit --mode test --gpu MI355X --leaderboard "$LEADERBOARD" "$py_file"
                
                echo -e "${YELLOW}[DRY RUN] Not actually submitting${NC}"
            fi
        done
    fi
done

echo ""
echo "=========================================="
echo "Submission complete!"
echo "=========================================="
