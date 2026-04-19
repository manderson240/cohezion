#!/bin/bash
# 🚀 Luma AMD Speedrun — Automated Submission Deployment
# Usage: ./deploy_submissions.sh [test|benchmark|leaderboard]

set -e

MODE=${1:-test}
LUMA_DIR="/home/mike-anderson/dev/cohezion/luma_speedrun"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=========================================="
echo "  Luma AMD Speedrun — Submission Deploy"
echo "  Mode: $MODE"
echo "  Time: $(date)"
echo "=========================================="
echo ""

# Submission registry
SUBMISSIONS=(
  "amd-moe-mxfp4:submission_fp8_blockscale_v2.py:MoE FP8 Blockscale v2"
  "amd-mixed-mla:submission_asm_decode_bypass.py:MLA ASM Decode Bypass"
  "amd-mxfp4-mm:submission_mfma_128x128_v1.py:GEMM MFMA 128x128"
)

RESULTS_FILE="$LUMA_DIR/.agent/deployment_results_$TIMESTAMP.json"
echo "{\"timestamp\": \"$TIMESTAMP\", \"mode\": \"$MODE\", \"results\": [" > "$RESULTS_FILE"

FIRST=true
for sub in "${SUBMISSIONS[@]}"; do
  IFS=':' read -r dir file desc <<< "$sub"
  
  echo "----------------------------------------"
  echo "🎯 $desc"
  echo "   File: $file"
  echo "   Dir: $dir"
  
  cd "$LUMA_DIR/$dir"
  
  if [ ! -f "$file" ]; then
    echo "   ❌ File not found, skipping"
    continue
  fi
  
  # Submit
  echo "   📤 Submitting to $MODE..."
  if timeout 600 popcorn-cli submit --mode "$MODE" --gpu MI355X \
       --leaderboard "$(echo $dir | sed 's/amd-//')" "$file" 2>&1 | tee "deploy_${file%.py}_$TIMESTAMP.log"; then
    
    # Extract results
    if [ "$MODE" == "test" ]; then
      if grep -q "Testing successful" "deploy_${file%.py}_$TIMESTAMP.log"; then
        STATUS="PASS"
        echo "   ✅ Test PASSED"
      else
        STATUS="FAIL"
        echo "   ❌ Test FAILED"
      fi
    elif [ "$MODE" == "benchmark" ]; then
      TIMES=$(grep "⏱" "deploy_${file%.py}_$TIMESTAMP.log" | sed 's/.*⏱ //; s/ ±.*//' | tr '\n' ',' | sed 's/,$//')
      STATUS="COMPLETE"
      echo "   📊 Times: $TIMES"
    else
      STATUS="SUBMITTED"
      echo "   🏆 Leaderboard submitted"
    fi
  else
    STATUS="TIMEOUT"
    echo "   ⏱️ Timeout or error"
  fi
  
  # Record result
  if [ "$FIRST" = true ]; then
    FIRST=false
  else
    echo "," >> "$RESULTS_FILE"
  fi
  echo -n "  {\"kernel\": \"$dir\", \"file\": \"$file\", \"status\": \"$STATUS\"}" >> "$RESULTS_FILE"
  
  echo ""
done

echo "" >> "$RESULTS_FILE"
echo "]}" >> "$RESULTS_FILE"

echo "=========================================="
echo "  Deployment Complete"
echo "  Results: $RESULTS_FILE"
echo "=========================================="

# Show summary
echo ""
echo "📊 Summary:"
cat "$RESULTS_FILE" | python3 -m json.tool 2>/dev/null || cat "$RESULTS_FILE"
