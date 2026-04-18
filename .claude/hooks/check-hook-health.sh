#!/usr/bin/env bash
# SessionStart hook: verify .git/hooks/* don't reference missing scripts.
#
# Rationale: auto-generated git hooks can reference repo files that get
# renamed/removed, leaving the hook itself intact but broken. A broken
# pre-commit hook then blocks every future commit with a cryptic error.
# See src/cohezion/knowledge_graph/KEY_LEARNINGS.md L364.
#
# This hook warns (not blocks) at SessionStart — it's diagnostic, not gating.
# If a hook references a missing script, the user gets an explicit message
# naming the broken hook and the missing target.
#
# Exit code: always 0. This is informational only.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$REPO_ROOT" ]; then
    # Not in a git repo — nothing to check
    exit 0
fi

HOOKS_DIR="$REPO_ROOT/.git/hooks"
if [ ! -d "$HOOKS_DIR" ]; then
    exit 0
fi

broken_hooks=()

for hook in "$HOOKS_DIR"/*; do
    # Skip .sample, .disabled, non-executable
    base="$(basename "$hook")"
    case "$base" in
        *.sample|*.disabled|*~) continue ;;
    esac
    [ -x "$hook" ] || continue
    [ -f "$hook" ] || continue

    # Scan hook for repo-relative script refs (scripts/..., tools/..., etc.)
    # Extract anything that looks like a path to a .py/.sh/.js file inside the repo.
    # Use grep -oE for portable regex; false positives are OK (we only warn).
    refs=$(grep -oE '\b(scripts|tools|bin|\.git|src)/[A-Za-z0-9_./-]+\.(py|sh|js|mjs|ts)\b' "$hook" 2>/dev/null | sort -u)
    [ -z "$refs" ] && continue

    missing_for_hook=()
    while IFS= read -r ref; do
        # Strip leading ./ if any
        target="${ref#./}"
        if [ ! -e "$REPO_ROOT/$target" ]; then
            missing_for_hook+=("$target")
        fi
    done <<< "$refs"

    if [ "${#missing_for_hook[@]}" -gt 0 ]; then
        broken_hooks+=("$base: ${missing_for_hook[*]}")
    fi
done

if [ "${#broken_hooks[@]}" -gt 0 ]; then
    echo "[hook-health] WARNING: .git/hooks references missing repo files:" >&2
    for entry in "${broken_hooks[@]}"; do
        echo "  - $entry" >&2
    done
    echo "[hook-health] These hooks may fail silently. To disable:" >&2
    echo "  mv .git/hooks/<name> .git/hooks/<name>.disabled" >&2
    echo "[hook-health] This warning is non-blocking." >&2
fi

exit 0
