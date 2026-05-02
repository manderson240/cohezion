#!/bin/bash
DEADLINE=$(date -d "07:00" +%s)
COUNT=0
while [ $(date +%s) -lt $DEADLINE ]; do
    REMAINING=$(( ($(date -d "07:00" +%s) - $(date +%s)) / 60 ))
    COUNT=$((COUNT + 1))
    echo "=== Round $COUNT | $(date) | ${REMAINING}min remaining ===" >> cycles.log
    
    uv run python driver.py --kernel gemm --dry-run-llm --max-cycles 3 2>&1 | grep -E "(best=|synthetic)" >> cycles.log &
    uv run python driver.py --kernel mla --dry-run-llm --max-cycles 3 2>&1 | grep -E "(best=|synthetic)" >> cycles.log &
    uv run python driver.py --kernel moe --dry-run-llm --max-cycles 3 2>&1 | grep -E "(best=|synthetic)" >> cycles.log &
    
    wait
    
    echo "--- checkpoint $(date) ---" >> cycles.log
    for f in tree/*.json; do python3 -c "import json; d=json.load(open('$f')); active=sum(1 for n in d['nodes'].values() if n.get('status')=='active'); print(f\"{d['kernel_name']}: {len(d['nodes'])} nodes, {active} active\")" >> cycles.log; done
    
    sleep 60
done
echo "=== COMPLETE at $(date) ===" >> cycles.log
