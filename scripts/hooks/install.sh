#!/usr/bin/env bash
# Idempotent installer for cohezion git hooks.
# Wires the repo-tracked scripts/hooks/*.py into .git/hooks/* so every commit
# in the local clone fires the associated hook. Safe to re-run.
#
# Current hooks installed:
#   * vmodel_gate_post_commit.py — structural V-model gate recorder (fast path).
#   * experiential_learning_hook.py — narrative learning (routes through
#     scripts/delegate.py to the local fleet, 20s budget, non-blocking).
#
# Pattern: the .git/hooks/<name> file remains a thin shell wrapper that calls
# into the repo-tracked scripts. Local .git/hooks files are NOT version-controlled,
# but the logic they invoke IS. Cloners must run this script once post-clone.
#
# Usage:
#     bash scripts/hooks/install.sh
#
# Skip either hook at commit time:
#     VMODEL_GATE_DISABLE=1 git commit ...              # skip structural gate
#     EXPERIENTIAL_LEARNING_DISABLE=1 git commit ...    # skip narrative
#     VMODEL_GATE_DISABLE=1 EXPERIENTIAL_LEARNING_DISABLE=1 git commit ...

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
POST_COMMIT="$HOOKS_DIR/post-commit"
VMODEL_HOOK="$REPO_ROOT/scripts/hooks/vmodel_gate_post_commit.py"
NARRATIVE_HOOK="$REPO_ROOT/scripts/hooks/experiential_learning_hook.py"

for h in "$VMODEL_HOOK" "$NARRATIVE_HOOK"; do
    if [ ! -x "$h" ]; then
        chmod +x "$h"
    fi
done

ensure_stanza() {
    # $1 = marker to grep for; $2 = stanza body to append if missing
    local marker="$1"
    local stanza="$2"
    if ! grep -q "$marker" "$POST_COMMIT"; then
        printf '\n%s\n' "$stanza" >> "$POST_COMMIT"
        echo "Appended $marker stanza to $POST_COMMIT"
    else
        echo "$marker already installed"
    fi
}

VMODEL_STANZA='# Cohezion V-model gate recorder (added by scripts/hooks/install.sh)
_repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -n "$_repo_root" ] && [ -x "$_repo_root/scripts/hooks/vmodel_gate_post_commit.py" ]; then
    python3 "$_repo_root/scripts/hooks/vmodel_gate_post_commit.py" 2>/dev/null || true
fi'

NARRATIVE_STANZA='# Cohezion experiential learning — narrative learnings via local fleet (20s budget)
_repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -n "$_repo_root" ] && [ -x "$_repo_root/scripts/hooks/experiential_learning_hook.py" ]; then
    python3 "$_repo_root/scripts/hooks/experiential_learning_hook.py" 2>/dev/null || true
fi'

# Create post-commit with our stanzas if missing; otherwise idempotently add them.
if [ ! -f "$POST_COMMIT" ]; then
    cat > "$POST_COMMIT" <<SHELL
#!/bin/sh
$VMODEL_STANZA

$NARRATIVE_STANZA
SHELL
    chmod +x "$POST_COMMIT"
    echo "Installed fresh .git/hooks/post-commit with vmodel_gate + experiential_learning hooks"
else
    ensure_stanza "vmodel_gate_post_commit.py" "$VMODEL_STANZA"
    ensure_stanza "experiential_learning_hook.py" "$NARRATIVE_STANZA"
fi

# Sanity-check: can each hook script import cleanly?
for hook_name in vmodel_gate_post_commit experiential_learning_hook; do
    if python3 -c "import sys; sys.path.insert(0, '$REPO_ROOT/scripts/hooks'); import $hook_name" 2>/dev/null; then
        echo "$hook_name imports clean."
    else
        echo "Warning: $hook_name failed import check (non-fatal)"
    fi
done

echo "Done. Next commit records vmodel_gate + narrative_learning in SurrealDB cohezion/main."
echo "Skip: VMODEL_GATE_DISABLE=1 or EXPERIENTIAL_LEARNING_DISABLE=1"
