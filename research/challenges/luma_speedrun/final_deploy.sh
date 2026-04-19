#!/bin/bash
# 🚀 Final Deployment Script — Luma AMD Speedrun
# Usage: ./final_deploy.sh [test|benchmark|leaderboard]

set -e

MODE=${1:-test}
LUMA_DIR="/home/mike-anderson/dev/cohezion/luma_speedrun"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=========================================="
echo "  FINAL DEPLOYMENT — Luma AMD Speedrun"
echo "  Mode: $MODE | Time: $(date)"
echo "=========================================="

# Top submissions by kernel
SUBMISSIONS=(
  # MoE
  "amd-moe-mxfp4:submission_fp8_blockscale_v2.py:MoE FP8 Blockscale"
  "amd-moe-mxfp4:submission_fp8_grouped_v3.py:MoE FP8 Grouped"
  "amd-moe-mxfp4:submission_shape_aware_v3.py:MoE Shape-Aware"
  "amd-moe-mxfp4:submission_fused_sort_gemm_v3.py:MoE Fused Sort+GEMM"
  "amd-moe-mxfp4:submission_breakthrough_moe.py:MoE Breakthrough"
  # MLA
  "amd-mixed-mla:submission_asm_decode_bypass.py:MLA ASM Bypass"
  "amd-mixed-mla:submission_splitk_aggressive_v3.py:MLA Split-K Aggressive"
  "amd-mixed-mla:submission_bf16_pure_v3.py:MLA BF16 Pure"
  "amd-mixed-mla:submission_multiwave_v3.py:MLA Multi-Wave"
  "amd-mixed-mla:submission_best_mla_final.py:MLA Best Final"
  # GEMM
  "amd-mxfp4-mm:submission_mfma_128x128_v1.py:GEMM MFMA 128x128"
  "amd-mxfp4-mm:submission_breakthrough_gemm.py:GEMM Breakthrough"
)

echo "Submissions to deploy: ${#SUBMISSIONS[@]}"
echo ""

for sub in "${SUBMISSIONS[@]}"; do
  IFS=':' read -r dir file desc <<< "$sub"
  
  echo "----------------------------------------"
  echo "🎯 $desc"
  
  cd "$LUMA_DIR/$dir"
  
  if [ ! -f "$file" ]; then
    echo "   ⚠️  File not found: $file"
    continue
  fi
  
  # Validate syntax first
  if python3 -m py_compile "$file" 2>/dev/null; then
    echo "   ✅ Syntax valid"
  else
    echo "   ❌ Syntax error — skipping"
    continue
  fi
  
  # Submit
  echo "   📤 Deploying to $MODE..."
  if timeout 600 popcorn-cli submit --mode "$MODE" --gpu MI355X \
       --leaderboard "$(echo $dir | sed 's/amd-//')" "$file" 2>&1 | tee "final_${file%.py}_$TIMESTAMP.log"; then
    echo "   ✅ Deployed successfully"
  else
    echo "   ⚠️  Deployment timeout or error"
  fi
  
  echo ""
done

echo "=========================================="
echo "  Deployment Complete"
echo "=========================================="
