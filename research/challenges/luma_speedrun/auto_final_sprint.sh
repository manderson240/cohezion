#!/bin/bash
# Autonomous final sprint — submits best candidates to leaderboard on hourly schedule
# Run with: nohup bash auto_final_sprint.sh > /tmp/final_sprint.log 2>&1 &

LUMA="/home/mike-anderson/dev/cohezion/luma_speedrun"
LOG="/tmp/final_sprint.log"

echo "=== FINAL SPRINT STARTED $(date) ===" >> $LOG

# Queue of leaderboard submissions (most promising first)
# Format: directory|filename|kernel
QUEUE=(
    "amd-mxfp4-mm|submission_asm_grid_search.py|GEMM"
    "amd-mxfp4-mm|submission_triton_dotscaled.py|GEMM"
    "amd-mixed-mla|submission_a16w16.py|MLA"
)

for entry in "${QUEUE[@]}"; do
    IFS='|' read -r dir file kernel <<< "$entry"
    echo "$(date): Submitting $kernel: $file to leaderboard" >> $LOG

    cd "$LUMA/$dir"
    RESULT=$(timeout 600 popcorn-cli submit --no-tui --mode leaderboard --gpu MI355X --leaderboard "$dir" "$file" 2>&1)

    if echo "$RESULT" | grep -q "Leaderboard run successful"; then
        echo "$(date): $kernel LEADERBOARD SUCCESS" >> $LOG
        echo "$RESULT" | grep "⏱" >> $LOG
    elif echo "$RESULT" | grep -q "Rate limit"; then
        echo "$(date): $kernel RATE LIMITED — waiting 1 hour" >> $LOG
    else
        echo "$(date): $kernel RESULT: $(echo "$RESULT" | tail -3)" >> $LOG
    fi

    # Wait 1 hour between leaderboard submissions
    echo "$(date): Sleeping 3600s for rate limit" >> $LOG
    sleep 3600
done

echo "=== FINAL SPRINT COMPLETE $(date) ===" >> $LOG
