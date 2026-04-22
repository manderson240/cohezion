#!/usr/bin/env bash
# Idempotent installer for cohezion git hooks.
# Wires the repo-tracked scripts/hooks/*.py into .git/hooks/* so every commit
# in the local clone fires the associated hook. Safe to re-run.
#
# Current hooks installed:
#   * vmodel_gate_post_commit.py — structural V-model gate recorder (fast path).
#
# Pattern: the .git/hooks/<name> file remains a thin shell wrapper that calls
# into the repo-tracked scripts. Local .git/hooks files are NOT version-controlled,
# but the logic they invoke IS. Cloners must run this script once post-clone.
#
# Usage:
#     bash scripts/hooks/install.sh
#
# Skip VMODEL hook at commit time:
#     VMODEL_GATE_DISABLE=1 git commit ...

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
POST_COMMIT="$HOOKS_DIR/post-commit"
VMODEL_HOOK="$REPO_ROOT/scripts/hooks/vmodel_gate_post_commit.py"

if [ ! -x "$VMODEL_HOOK" ]; then
    chmod +x "$VMODEL_HOOK"
fi

# Create post-commit with our stanza if missing; otherwise idempotently add it.
if [ ! -f "$POST_COMMIT" ]; then
    cat > "$POST_COMMIT" <<'SHELL'
#!/bin/sh
_repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -n "$_repo_root" ] && [ -x "$_repo_root/scripts/hooks/vmodel_gate_post_commit.py" ]; then
    python3 "$_repo_root/scripts/hooks/vmodel_gate_post_commit.py" 2>/dev/null || true
fi
SHELL
    chmod +x "$POST_COMMIT"
    echo "Installed fresh .git/hooks/post-commit with vmodel_gate hook"
elif ! grep -q "vmodel_gate_post_commit.py" "$POST_COMMIT"; then
    # Existing post-commit present (e.g. from `entire enable`). Insert our stanza.
    # Insert before the final closing line so chain/fall-through logic keeps working.
    cat >> "$POST_COMMIT" <<'SHELL'

# Cohezion V-model gate recorder (added by scripts/hooks/install.sh)
_repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -n "$_repo_root" ] && [ -x "$_repo_root/scripts/hooks/vmodel_gate_post_commit.py" ]; then
    python3 "$_repo_root/scripts/hooks/vmodel_gate_post_commit.py" 2>/dev/null || true
fi
SHELL
    echo "Appended vmodel_gate hook to existing .git/hooks/post-commit"
else
    echo "vmodel_gate hook already installed in .git/hooks/post-commit"
fi

# Sanity-check: can the hook actually run?
if python3 "$VMODEL_HOOK" --help 2>/dev/null >/dev/null || python3 -c "import sys; sys.path.insert(0, '$REPO_ROOT/scripts/hooks'); import vmodel_gate_post_commit" 2>/dev/null; then
    echo "Hook script imports clean."
else
    echo "Warning: hook script failed import check (non-fatal)"
fi

echo "Done. Next commit in this repo will record a vmodel_gate in SurrealDB cohezion/main."
echo "To skip: VMODEL_GATE_DISABLE=1 git commit ..."
