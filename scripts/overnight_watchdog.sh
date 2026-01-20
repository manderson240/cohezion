#!/bin/bash
# Watchdog script - ensures all workers keep running until 8:00 AM EST
# Runs every 30 minutes to check and restart any failed workers

TARGET_END_TIME="08:00"
COHEZION_ROOT="/home/mike-anderson/dev/cohezion"
cd "$COHEZION_ROOT"

while true; do
    CURRENT_TIME=$(date +%H:%M)
    
    # Stop if we've reached 8:00 AM
    if [[ "$CURRENT_TIME" > "$TARGET_END_TIME" || "$CURRENT_TIME" == "$TARGET_END_TIME" ]]; then
        echo "$(date): Reached target time $TARGET_END_TIME. Watchdog exiting."
        break
    fi
    
    echo "$(date): Watchdog check - ensuring workers active until $TARGET_END_TIME"
    
    # Check main coordinator
    if ! pgrep -f "overnight_simple.py" > /dev/null; then
        echo "  ⚠️  Main coordinator offline - RESTARTING"
        nohup python3 -u scripts/overnight_simple.py > logs/overnight_live.log 2>&1 &
    fi
    
    # Check HIHO workers (should have at least 20 active)
    HIHO_COUNT=$(pgrep -f "hiho_worker.py" | wc -l)
    if [ "$HIHO_COUNT" -lt 20 ]; then
        echo "  ⚠️  Only $HIHO_COUNT HIHO workers (expected 24) - launching more"
        for i in {1..24}; do
            if ! pgrep -f "hiho_worker.py $i" > /dev/null; then
                nohup uv run python scripts/hiho_worker.py $i > logs/hiho_worker_${i}.log 2>&1 &
                sleep 0.5
            fi
        done
    fi
    
    # Check Ollama workers (should have 6 active)
    OLLAMA_COUNT=$(pgrep -f "ollama_worker.py" | wc -l)
    if [ "$OLLAMA_COUNT" -lt 6 ]; then
        echo "  ⚠️  Only $OLLAMA_COUNT Ollama workers (expected 6) - launching more"
        for i in {1..6}; do
            if ! pgrep -f "ollama_worker.py $i" > /dev/null; then
                nohup python3 -u scripts/ollama_worker.py $i > logs/ollama_worker_${i}.log 2>&1 &
                sleep 0.5
            fi
        done
    fi
    
    echo "  ✓ Status: $HIHO_COUNT HIHO, $OLLAMA_COUNT Ollama workers active"
    
    # Sleep for 30 minutes before next check
    sleep 1800
done

echo "$(date): Mission complete at $TARGET_END_TIME. All workers can shut down."
