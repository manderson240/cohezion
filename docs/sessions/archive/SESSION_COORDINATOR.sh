#!/bin/bash
# SESSION_COORDINATOR.sh - Manages multiple overnight sessions safely
# Prevents conflicts and ensures submissions keep flowing

LOCK_BASE="/tmp/luma_coord"
mkdir -p "$LOCK_BASE"

log() {
    echo "[$(date '+%H:%M:%S')] COORD: $1" | tee -a "$LOCK_BASE/coordinator.log"
}

# Register this session
SESSION_ID=$$
echo "$SESSION_ID $(hostname) $(date +%s)" > "$LOCK_BASE/session.$SESSION_ID"

cleanup() {
    rm -f "$LOCK_BASE/session.$SESSION_ID"
    rm -f "$LOCK_BASE/heartbeat.$SESSION_ID"
}
trap cleanup EXIT

# Heartbeat thread
heartbeat() {
    while true; do
        echo "$(date +%s)" > "$LOCK_BASE/heartbeat.$SESSION_ID"
        sleep 60
    done
}
heartbeat &
HEARTBEAT_PID=$!

# Assign this session a "slot"
assign_slot() {
    for i in 1 2 3; do
        if [[ ! -f "$LOCK_BASE/slot_$i" ]]; then
            echo "$SESSION_ID" > "$LOCK_BASE/slot_$i"
            echo "$i"
            return
        fi
    done
    echo "wait"
}

# Claim slot
SLOT="$(assign_slot)"
while [[ "$SLOT" == "wait" ]]; do
    log "Waiting for available slot..."
    sleep 30
    SLOT="$(assign_slot)"
done

log "Session $SESSION_ID assigned to slot $SLOT"

# Calculate which kernel this session owns
# Slot 1: MLA, Slot 2: MoE, Slot 3: GEMM
case "$SLOT" in
    1)
        ASSIGNED_KERNEL="aml"
        KERNEL_NAME="amd-mixed-mla"
        ;;
    2)
        ASSIGNED_KERNEL="moe"
        KERNEL_NAME="amd-moe-mxfp4"
        ;;
    3)
        ASSIGNED_KERNEL="gemm"
        KERNEL_NAME="amd-mxfp4-mm"
        ;;
esac

log "Session $SESSION_ID owns kernel: $ASSIGNED_KERNEL ($KERNEL_NAME)"

# Run the production system in "single kernel mode"
export ASSIGNED_KERNEL
export KERNEL_NAME
log "Starting dedicated submission loop for $ASSIGNED_KERNEL"

# Run the production script in once-per-loop mode
while true; do
    log "Submitting to $ASSIGNED_KERNEL..."
    
    cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun/$KERNEL_NAME
    
    timeout 600 popcorn-cli submit submission.py \
        --mode leaderboard \
        --gpu MI355X \
        --leaderboard "$KERNEL_NAME" \
        --no-tui 2>&1 | tee -a "$LOCK_BASE/${ASSIGNED_KERNEL}_session_${SESSION_ID}.log" | while read line; do
            if echo "$line" | grep -q "Submission #"; then
                log "✅ $ASSIGNED_KERNEL: $line"
            elif echo "$line" | grep -q "Rate limit"; then
                log "⏳ $ASSIGNED_KERNEL: Rate limited - waiting"
            elif echo "$line" | grep -q "passed"; then
                log "✓ $ASSIGNED_KERNEL: Test passed"
            fi
        done
    
    log "Sleeping 50 minutes before next $ASSIGNED_KERNEL submission..."
    sleep 3000
done

# Cleanup
cleanup
kill $HEARTBEAT_PID 2>/dev/null
