#!/usr/bin/env bash
# Guardrailed single-tick runner for a PERSISTENT cohezion self-improvement loop.
#
# Invoked by a systemd user timer (see cohezion-build-loop.timer). Runs ONE /loop tick
# headless, then exits; the timer re-fires on cadence. Survives session-close + reboot.
#
# Charter guardrails (Observable AI / bounded autonomy / rollback), in order:
#   1. KILL SWITCH   — `.loop-off` in the repo halts everything immediately.
#   2. BRANCH GUARD  — refuses main/develop/master; only an allowed feature-branch prefix.
#   3. BUDGET CAP    — a daily tick ceiling (proxy for $ spend); stops when reached.
#   4. FLOCK         — no overlapping ticks.
#   5. PERMISSION    — SAFE DEFAULT (acceptEdits: cannot run Bash → cannot commit → effectively
#                      a dry run). Full autonomy requires you to set COHEZION_LOOP_PERMISSION_MODE
#                      =bypassPermissions DELIBERATELY (that is the money-spending, self-committing
#                      switch — the charter's human-in-the-loop trigger).
#   6. LOG           — every tick + every guardrail decision appended to .loop-state/loop.log.
set -uo pipefail

REPO="${COHEZION_LOOP_REPO:-/home/mike-anderson/dev/cohezion}"
cd "$REPO" || { echo "repo not found: $REPO" >&2; exit 1; }

STATE="$REPO/.loop-state"
LOG="$STATE/loop.log"
KILL="$REPO/.loop-off"
LOCK="$STATE/tick.lock"
BUDGET_FILE="$STATE/ticks-$(date +%F).count"
MAX_TICKS="${COHEZION_LOOP_MAX_TICKS:-40}"
PERMISSION_MODE="${COHEZION_LOOP_PERMISSION_MODE:-acceptEdits}"   # SAFE default; see guardrail 5
PROMPT_FILE="${COHEZION_LOOP_PROMPT_FILE:-$REPO/scripts/loop/build_loop_prompt.txt}"
mkdir -p "$STATE"
log() { echo "[$(date -Is)] $*" >>"$LOG"; }

# 1. KILL SWITCH
if [ -f "$KILL" ]; then log "KILL: .loop-off present → skip"; exit 0; fi

# 2. BRANCH GUARD — never commit on a protected branch
BR="$(git -C "$REPO" branch --show-current 2>/dev/null || echo '?')"
case "$BR" in
  main|develop|master) log "BRANCH-GUARD: on protected '$BR' → refuse"; exit 0 ;;
esac
case "$BR" in
  feat/*|fix/*|kaggle/*|isolated/*|spec/*) : ;;
  *) log "BRANCH-GUARD: '$BR' not an allowed prefix → refuse"; exit 0 ;;
esac

# 3. DAILY BUDGET CAP
COUNT="$(cat "$BUDGET_FILE" 2>/dev/null || echo 0)"
if [ "$COUNT" -ge "$MAX_TICKS" ]; then log "BUDGET: $COUNT/$MAX_TICKS ticks today → stop"; exit 0; fi

# 4. FLOCK — single tick at a time
exec 9>"$LOCK"
if ! flock -n 9; then log "LOCK: a tick is already running → skip"; exit 0; fi

# 5/6. RUN ONE TICK
echo "$((COUNT + 1))" >"$BUDGET_FILE"
log "TICK $((COUNT + 1))/$MAX_TICKS on '$BR' (perm=$PERMISSION_MODE) — start"
if [ "$PERMISSION_MODE" = "acceptEdits" ]; then
  log "NOTE: SAFE default permission mode — Bash is blocked, so this tick cannot commit (dry run). \
Set COHEZION_LOOP_PERMISSION_MODE=bypassPermissions to enable full autonomy (spends \$, self-commits)."
fi
PROMPT="$(cat "$PROMPT_FILE")"
timeout 1800 claude --print --permission-mode "$PERMISSION_MODE" "$PROMPT" >>"$LOG" 2>&1
rc=$?
log "TICK done (claude rc=$rc)"
exit 0
