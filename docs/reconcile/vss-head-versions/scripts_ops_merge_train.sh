#!/usr/bin/env bash
# merge_train.sh — stack branches onto a rolling candidate via pure git plumbing.
#
# Works while .git/worktrees is READ-ONLY (no worktree, no porcelain merge needed):
# merge-tree computes the merge in the object DB; commit-tree records it with REAL
# merge parents (never squash multi-commit branches). The caller advances the target
# ref afterwards with:  git update-ref refs/heads/main <candidate> <old-main>
# (third arg is compare-and-swap oldvalue, NOT a message).
#
# Gate the FINAL candidate once (git archive | tar -x + PYTHONPATH override), bisect
# only on failure. Full runbook + traps:
#   ~/vaults/cohezion-vault/skills/plumbing-merge-train-ro-worktrees/SKILL.md
#
# Usage: merge_train.sh <start-ref> <branch>...
# Prints the final candidate commit sha. Conflicting branches are skipped (reported
# on stderr); resolve those separately via a temp GIT_INDEX_FILE + update-index.
set -uo pipefail
REPO="${MERGE_TRAIN_REPO:-/home/mike-anderson/dev/cohezion}"
cd "$REPO"

CANDIDATE=$(git rev-parse "${1:?start ref}")
shift

for BRANCH in "$@"; do
  TREE_OUT=$(git merge-tree --write-tree "$CANDIDATE" "$BRANCH" 2>&1)
  if [ $? -ne 0 ]; then
    echo "SKIP-CONFLICT $BRANCH" >&2
    echo "$TREE_OUT" | grep "^CONFLICT" | head -5 >&2
    continue
  fi
  TREE=$(echo "$TREE_OUT" | head -1)
  # Empty merge = already integrated relative to the candidate (the only honest
  # integration test — ancestry and `git cherry` both lie after squash merges).
  if [ "$TREE" = "$(git rev-parse "$CANDIDATE^{tree}")" ]; then
    echo "SKIP-INTEGRATED $BRANCH" >&2
    continue
  fi
  CANDIDATE=$(git commit-tree "$TREE" -p "$CANDIDATE" -p "$(git rev-parse "$BRANCH")" \
    -m "Merge branch '$BRANCH' into main (landing train $(date +%Y-%m-%d))")
  echo "MERGED $BRANCH -> $CANDIDATE" >&2
done

echo "$CANDIDATE"
