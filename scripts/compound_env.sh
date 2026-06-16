#!/usr/bin/env bash
# compound_env.sh — Cohezion compound engineering tmux environment
#
# Creates a named tmux session "cohezion" with 4 panes:
#   Pane 0 (top-left):  Compound REPL  — uv run python -i scripts/drivers/compound_cycle.py
#   Pane 1 (top-right): Inference health watch — curl -s loop against :13305/api/v1/models
#   Pane 2 (bot-left):  EventBus tail   — tail the compound event log
#   Pane 3 (bot-right): SurrealDB tail  — ws://localhost:8001 live query
#
# Usage:
#   ./scripts/compound_env.sh          # create (or attach if already running)
#   tmux attach-session -t cohezion    # re-attach later

SESSION="cohezion"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Check for existing session ───────────────────────────────────────────────
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Session '$SESSION' already exists."
    echo ""
    echo "Attach with:"
    echo "  tmux attach-session -t $SESSION"
    exit 0
fi

# ── Create session with first window ────────────────────────────────────────
# Start detached; window 0, pane 0 = compound REPL
tmux new-session -d -s "$SESSION" -x 220 -y 50 \
    -c "$REPO_ROOT" \
    "uv run python -i scripts/drivers/compound_cycle.py; exec bash"

# ── Split top pane: Pane 1 = inference health watch (right half of top) ─────
tmux split-window -h -t "$SESSION:0.0" \
    -c "$REPO_ROOT" \
    "watch -n 5 'curl -s --max-time 2 http://localhost:13305/api/v1/models 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); [print(m[\\\"id\\\"], m.get(\\\"state\\\",\\\"?\\\")) for m in d.get(\\\"data\\\",[])[:12]]\" 2>/dev/null || echo \"[inference router offline]\"; exec bash'"

# ── Select top-left (pane 0), split vertically: Pane 2 = EventBus tail ──────
tmux select-pane -t "$SESSION:0.0"
tmux split-window -v -t "$SESSION:0.0" \
    -c "$REPO_ROOT" \
    "tail -F ~/.cohezion/event_bus.jsonl 2>/dev/null || (echo '[EventBus log not found — will appear when compound loop starts]'; exec bash)"

# ── Select top-right (pane 1), split vertically: Pane 3 = SurrealDB tail ────
tmux select-pane -t "$SESSION:0.1"
tmux split-window -v -t "$SESSION:0.1" \
    -c "$REPO_ROOT" \
    "watch -n 3 'curl -s http://localhost:8001/health 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); print(\\\"SurrealDB:\\\", d)\" 2>/dev/null || echo \"[SurrealDB offline — start with: surreal start --log info]\"; exec bash'"

# ── Even out pane layout ─────────────────────────────────────────────────────
tmux select-layout -t "$SESSION:0" tiled

# ── Focus top-left (REPL) ────────────────────────────────────────────────────
tmux select-pane -t "$SESSION:0.0"

echo "Session '$SESSION' created with 4 panes:"
echo "  [0] Compound REPL        (top-left)"
echo "  [1] Inference health     (top-right)"
echo "  [2] EventBus tail        (bottom-left)"
echo "  [3] SurrealDB tail       (bottom-right)"
echo ""
echo "Attach with:"
echo "  tmux attach-session -t $SESSION"
