#!/bin/bash
# AMD x GPU MODE — Batch submission script
# Run: bash submit_all.sh [test|benchmark|leaderboard]
#
# Prerequisites:
#   1. popcorn-cli installed: curl -fsSL https://raw.githubusercontent.com/gpu-mode/popcorn-cli/main/install.sh | bash
#   2. Registered: popcorn-cli register github
#   3. ~/.popcorn.yaml exists

set -euo pipefail

MODE="${1:-test}"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== AMD Speedrun Submission (mode: $MODE) ==="
echo "Date: $(date -u)"
echo ""

# Check auth
if [ ! -f ~/.popcorn.yaml ]; then
    echo "ERROR: ~/.popcorn.yaml not found. Run: popcorn-cli register github"
    exit 1
fi

submit() {
    local kernel="$1"
    local leaderboard="$2"
    local file="$3"

    echo "──────────────────────────────────────────"
    echo "Submitting: $kernel ($MODE)"
    echo "File: $file"
    echo ""

    if [ ! -f "$file" ]; then
        echo "  ERROR: File not found: $file"
        return 1
    fi

    popcorn-cli submit \
        --no-tui \
        --mode "$MODE" \
        --gpu MI355X \
        --leaderboard "$leaderboard" \
        "$file" 2>&1 | tee "/tmp/popcorn_${kernel}_${MODE}.log"

    echo ""
    echo "  Log saved: /tmp/popcorn_${kernel}_${MODE}.log"
    echo ""
}

# Submit in priority order (MoE=1500pts, MLA=1250pts, GEMM=1000pts)
echo "=== Priority 1: MoE (1500 pts max) ==="
submit "moe" "amd-moe-mxfp4" "$DIR/amd-moe-mxfp4/submission.py"

echo "=== Priority 2: MLA (1250 pts max) ==="
submit "mla" "amd-mixed-mla" "$DIR/amd-mixed-mla/submission.py"

echo "=== Priority 3: GEMM (1000 pts max) ==="
submit "gemm" "amd-mxfp4-mm" "$DIR/amd-mxfp4-mm/submission.py"

echo ""
echo "=== All submissions complete ==="
echo "Check logs in /tmp/popcorn_*.log"

# If test mode passed, suggest benchmark
if [ "$MODE" = "test" ]; then
    echo ""
    echo "Next steps:"
    echo "  1. Check output for PASS/FAIL"
    echo "  2. If all pass: bash $0 benchmark"
    echo "  3. If benchmark looks good: bash $0 leaderboard"
fi
