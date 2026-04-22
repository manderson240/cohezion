#!/usr/bin/env bash
# Idempotent installer for cohezion git hooks.
# Wires the repo-tracked scripts/hooks/*.py into .git/hooks/* so every commit
# in the local clone fires the associated hook. Safe to re-run.
#
# Current hooks installed:
#   * post-commit: vmodel_gate_post_commit.py — structural V-model gate recorder.
#   * post-commit: experiential_learning_hook.py — narrative learning via local fleet.
#   * pre-push:    session_end.py — aggregate retrospection + SkillRefiner wiring.
#
# Pattern: the .git/hooks/<name> file remains a thin shell wrapper that calls
# into the repo-tracked scripts. Local .git/hooks files are NOT version-controlled,
# but the logic they invoke IS. Cloners must run this script once post-clone.
#
# Usage:
#     bash scripts/hooks/install.sh
#
# Skip at commit/push time:
#     VMODEL_GATE_DISABLE=1 git commit ...              # skip structural gate
#     EXPERIENTIAL_LEARNING_DISABLE=1 git commit ...    # skip narrative
#     SESSION_END_DISABLE=1 git push ...                # skip retrospection
#     (combine freely)

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
POST_COMMIT="$HOOKS_DIR/post-commit"
PRE_PUSH="$HOOKS_DIR/pre-push"
VMODEL_HOOK="$REPO_ROOT/scripts/hooks/vmodel_gate_post_commit.py"
NARRATIVE_HOOK="$REPO_ROOT/scripts/hooks/experiential_learning_hook.py"
SESSION_END_SCRIPT="$REPO_ROOT/scripts/session_end.py"

for h in "$VMODEL_HOOK" "$NARRATIVE_HOOK" "$SESSION_END_SCRIPT"; do
    if [ ! -x "$h" ]; then
        chmod +x "$h"
    fi
done

ensure_stanza() {
    # $1 = target hook file; $2 = marker to grep for; $3 = stanza body
    local target="$1"
    local marker="$2"
    local stanza="$3"
    if [ ! -f "$target" ] || ! grep -q "$marker" "$target"; then
        # File might not exist yet — caller handles that path separately.
        if [ -f "$target" ]; then
            printf '\n%s\n' "$stanza" >> "$target"
            echo "Appended $marker stanza to $target"
        fi
    else
        echo "$marker already installed in $(basename "$target")"
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

# Pre-push: session_end aggregates per-session vmodel_gate + narrative_learning
# rows into a RetrospectionEngine summary + SkillRefiner refinement pass, then
# writes a markdown to ~/vaults/cohezion-vault/retrospections/<session>.md.
# Non-blocking: failure never prevents a push. Use venv python so cohezion
# imports resolve (same L367 pattern as experiential_learning_hook.py).
# Set SESSION_END_DISABLE=1 to skip (e.g. for CI pushes).
SESSION_END_STANZA='# Cohezion session-end retrospection (pre-push)
if [ "${SESSION_END_DISABLE:-}" != "1" ]; then
    _repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"
    if [ -n "$_repo_root" ] && [ -x "$_repo_root/scripts/session_end.py" ]; then
        _venv_py="$_repo_root/.venv/bin/python3"
        if [ -x "$_venv_py" ]; then
            # Fire and forget — retrospection is informational, must not block push
            "$_venv_py" "$_repo_root/scripts/session_end.py" 2>/dev/null || true
        fi
    fi
fi
exit 0'

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
    ensure_stanza "$POST_COMMIT" "vmodel_gate_post_commit.py" "$VMODEL_STANZA"
    ensure_stanza "$POST_COMMIT" "experiential_learning_hook.py" "$NARRATIVE_STANZA"
fi

# Create/extend pre-push with session_end stanza.
if [ ! -f "$PRE_PUSH" ]; then
    cat > "$PRE_PUSH" <<SHELL
#!/bin/sh
$SESSION_END_STANZA
SHELL
    chmod +x "$PRE_PUSH"
    echo "Installed fresh .git/hooks/pre-push with session_end hook"
else
    ensure_stanza "$PRE_PUSH" "session_end.py" "$SESSION_END_STANZA"
fi

# Sanity-check: can each hook script import cleanly?
for hook_name in vmodel_gate_post_commit experiential_learning_hook; do
    if python3 -c "import sys; sys.path.insert(0, '$REPO_ROOT/scripts/hooks'); import $hook_name" 2>/dev/null; then
        echo "$hook_name imports clean."
    else
        echo "Warning: $hook_name failed import check (non-fatal)"
    fi
done

echo "Done. Commit: records vmodel_gate + narrative_learning. Push: session_end aggregates."
echo "Skip: VMODEL_GATE_DISABLE=1 / EXPERIENTIAL_LEARNING_DISABLE=1 / SESSION_END_DISABLE=1"
