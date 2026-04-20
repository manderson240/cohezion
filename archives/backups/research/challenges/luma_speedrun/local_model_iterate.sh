#!/bin/bash
# Local model kernel iteration — uses small fast models for rapid variants
# These run entirely on local GPU, zero API cost, fast response

KERNEL=${1:-gemm}
MODEL=${2:-phi3:mini}  # Smallest/fastest for rapid iteration
LUMA="/home/mike-anderson/dev/cohezion/luma_speedrun"

case $KERNEL in
  gemm) DIR="amd-mxfp4-mm"; LB="amd-mxfp4-mm"; BEST="submission.py" ;;
  moe)  DIR="amd-moe-mxfp4"; LB="amd-moe-mxfp4"; BEST="submission.py" ;;
  mla)  DIR="amd-mixed-mla"; LB="amd-mixed-mla"; BEST="submission.py" ;;
esac

echo "Local model iteration: $KERNEL via $MODEL"
ITER=0
while true; do
  ITER=$((ITER + 1))
  PROMPT="Optimize this GPU kernel for AMD MI355X. Output ONLY the complete Python file.
CONSTRAINTS: BLOCK_K>=128 for Triton, use B_q not B_shuffle for MFMA, only GPU compute changes help.
$(cat $LUMA/$DIR/$BEST)"
  
  FILE="$LUMA/$DIR/submission_local_${KERNEL}_${ITER}.py"
  echo "$PROMPT" | timeout 60 ollama run "$MODEL" 2>/dev/null > "$FILE"
  
  if [ -s "$FILE" ] && python3 -c "import ast; ast.parse(open('$FILE').read())" 2>/dev/null; then
    echo "Iter $ITER: valid ($MODEL), $(wc -l < "$FILE") lines"
  else
    echo "Iter $ITER: invalid, skipping"
    rm -f "$FILE"
  fi
  sleep 10
done
