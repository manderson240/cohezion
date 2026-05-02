#!/bin/sh
# Pre-commit guard — block Kaggle competition work on non-kaggle branches.
#
# Per ~/.claude/rules/kaggle-portfolio.md:
#   "Don't do Kaggle work on isolated/session-oom-modularity — use the worktrees"
#
# Before this guard: ~13 NeuroGolf/ARC/Nemotron commits landed on
# isolated/session-oom-modularity instead of kaggle/agi-golf or
# kaggle/nemotron-june, sweeping up unrelated session work as byproducts.
#
# After this guard: commits that touch Kaggle competition paths on any
# branch NOT matching kaggle/* are refused with a pointer to the worktree.
# This catches drift at the point of commit, not after the fact.
#
# Scope — files under these paths trigger the guard:
#   * src/cohezion/competition/neurogolf/
#   * src/cohezion/competition/arc_agi_3/
#   * src/cohezion/competition/arc_prize_paper_track/
#   * src/cohezion/competition/gemma_hackathon/
#   * src/cohezion/competition/sei_accelathon/
#   * Any file matching *kaggle_submission* or *nemotron* pattern
#
# Bypass — any of these skip the guard:
#   * Branch name starts with kaggle/  (intended use case)
#   * KAGGLE_GUARD_DISABLE=1 env var   (explicit operator override)
#
# Exit codes:
#   0 = allowed to commit
#   1 = blocked (message on stderr)

set -eu

# Bypass #1: operator override
if [ "${KAGGLE_GUARD_DISABLE:-}" = "1" ]; then
    exit 0
fi

# Bypass #2: already on a kaggle/* branch — intended target
branch=$(git symbolic-ref --short HEAD 2>/dev/null || echo "DETACHED")
case "$branch" in
    kaggle/*)
        exit 0
        ;;
esac

# Check staged files for Kaggle paths
staged=$(git diff --cached --name-only 2>/dev/null || true)
if [ -z "$staged" ]; then
    # Nothing staged — probably a merge/amend; let it through
    exit 0
fi

violating=$(echo "$staged" | grep -E \
    "^src/cohezion/competition/(neurogolf|arc_agi_3|arc_prize_paper_track|gemma_hackathon|sei_accelathon)/|kaggle_submission|nemotron" \
    || true)

if [ -z "$violating" ]; then
    # No Kaggle paths staged — allow
    exit 0
fi

# Blocked: print guidance
printf '\n[kaggle-branch-guard] BLOCKED: Kaggle competition files staged on branch "%s"\n' "$branch" >&2
printf '\nFiles that triggered the guard:\n' >&2
echo "$violating" | sed 's/^/  - /' >&2
printf '\nPer ~/.claude/rules/kaggle-portfolio.md, Kaggle work belongs in a dedicated worktree:\n' >&2
printf '  * AGI-Golf / NeuroGolf / ARC-AGI work → .worktrees/agi-golf     [kaggle/agi-golf]\n' >&2
printf '  * Nemotron reasoning challenge         → .worktrees/nemotron-june [kaggle/nemotron-june]\n' >&2
printf '\nRecommended workflow:\n' >&2
printf '  cd .worktrees/agi-golf        # or nemotron-june\n' >&2
printf '  git add <the-files>\n' >&2
printf '  git commit -m "..."\n' >&2
printf '\nEscape hatch (use sparingly, and update kaggle-portfolio.md if persistent):\n' >&2
printf '  KAGGLE_GUARD_DISABLE=1 git commit ...\n' >&2
exit 1
