#!/bin/bash
# AMD x GPU MODE — Submit variant kernels for testing
# Tests ALL variants per kernel to find the fastest one
# Run: bash submit_variants.sh [kernel] [mode]
#   kernel: gemm|mla|moe|all (default: all)
#   mode: test|benchmark (default: test)

set -euo pipefail

KERNEL="${1:-all}"
MODE="${2:-test}"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Variant Testing (kernel: $KERNEL, mode: $MODE) ==="
echo ""

submit() {
    local name="$1"
    local leaderboard="$2"
    local file="$3"

    echo "── $name ──"
    if [ ! -f "$file" ]; then
        echo "  SKIP (file not found)"
        return
    fi

    local logfile="/tmp/popcorn_variant_$(basename "$file" .py)_${MODE}.log"
    popcorn-cli submit --no-tui --mode "$MODE" --gpu MI355X --leaderboard "$leaderboard" "$file" 2>&1 | tee "$logfile"
    echo "  → Log: $logfile"
    echo ""

    # Rate limit: wait 10s between submissions
    sleep 10
}

if [ "$KERNEL" = "gemm" ] || [ "$KERNEL" = "all" ]; then
    echo "═══ GEMM Variants ═══"
    submit "gemm-main" "amd-mxfp4-mm" "$DIR/amd-mxfp4-mm/submission.py"
    submit "gemm-fused-quant" "amd-mxfp4-mm" "$DIR/variants/gemm/submission_fused_quant.py"
    submit "gemm-prealloc" "amd-mxfp4-mm" "$DIR/variants/gemm/submission_prealloc.py"
    submit "gemm-loadinline" "amd-mxfp4-mm" "$DIR/variants/gemm/submission_loadinline_mfma.py"
    submit "gemm-triton-dotscaled" "amd-mxfp4-mm" "$DIR/variants/gemm/submission_triton_dotscaled.py"
fi

if [ "$KERNEL" = "mla" ] || [ "$KERNEL" = "all" ]; then
    echo "═══ MLA Variants ═══"
    submit "mla-main" "amd-mixed-mla" "$DIR/amd-mixed-mla/submission.py"
    submit "mla-api-probe" "amd-mixed-mla" "$DIR/variants/mla/submission_api_probe.py"
    submit "mla-persistent" "amd-mixed-mla" "$DIR/variants/mla/submission_persistent.py"
    submit "mla-autosplit" "amd-mixed-mla" "$DIR/variants/mla/submission_autosplit.py"
    submit "mla-batched-bmm" "amd-mixed-mla" "$DIR/variants/mla/submission_batched_bmm.py"
    submit "mla-splits-1" "amd-mixed-mla" "$DIR/variants/mla/submission_splits_1.py"
fi

if [ "$KERNEL" = "moe" ] || [ "$KERNEL" = "all" ]; then
    echo "═══ MoE Variants ═══"
    submit "moe-main" "amd-moe-mxfp4" "$DIR/amd-moe-mxfp4/submission.py"
    submit "moe-splitk-tuned" "amd-moe-mxfp4" "$DIR/variants/moe/submission_splitk_tuned.py"
    submit "moe-envtuned" "amd-moe-mxfp4" "$DIR/variants/moe/submission_envtuned.py"
    submit "moe-block-64" "amd-moe-mxfp4" "$DIR/variants/moe/submission_block_64.py"
    submit "moe-block-128" "amd-moe-mxfp4" "$DIR/variants/moe/submission_block_128.py"
    submit "moe-sorting-opus" "amd-moe-mxfp4" "$DIR/variants/moe/submission_sorting_opus.py"
fi

echo "=== Variant testing complete ==="
