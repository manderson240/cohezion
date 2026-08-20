#!/usr/bin/env bash
# Snapshot a worktree's uncommitted work to a durable git ref, WITHOUT touching its index.
#
# WHY (2026-08-16): an OOM/reboot deleted a worktree directory mid-session. What survived was
# everything that had reached .git/objects plus a ref — including a commit whose BRANCH was
# later deleted by another session (the object stayed reachable via its own ref). What would
# have died was any uncommitted working-tree edit.
#
# So the durability rule for code is simply: get it into .git/objects early. This does that
# without `git add`, which matters because the two situations where you most need a snapshot
# are exactly the two where `git add` fails:
#   * a read-only .git/worktrees mount  -> "cannot create index.lock: Read-only file system"
#   * a session pinned to a worktree    -> git operations against the shared checkout refused
#
# Both are worked around by staging into a TEMP index and using plumbing. Nothing in the
# working tree or the worktree's own index is modified, so this is safe to run on dirty trees
# and safe to run repeatedly.
#
# Usage:
#   scripts/snapshot_worktree.sh                      # snapshot cwd's worktree
#   scripts/snapshot_worktree.sh /path/to/worktree
#
# Recover later with:
#   git log --oneline refs/snapshots/<name>
#   git checkout refs/snapshots/<name> -- <path>      # or cherry-pick / diff against it
set -euo pipefail

WT="${1:-$(pwd)}"
cd "$WT"

REPO_GIT=$(git rev-parse --git-common-dir)
NAME=$(basename "$WT")
STAMP=$(date +%Y%m%d-%H%M%S)
REF="refs/snapshots/${NAME}"

# Temp index somewhere writable, and NOT under the worktree (which may be the ro mount).
# XDG_RUNTIME_DIR is preferred but is frequently absent inside sandboxes, so probe rather
# than assume: a missing directory yields a confusing "cannot create index.lock" from git.
for CAND in "${XDG_RUNTIME_DIR:-}" "${TMPDIR:-}" /tmp; do
  [ -n "$CAND" ] && [ -d "$CAND" ] && [ -w "$CAND" ] && IDXDIR="$CAND" && break
done
IDX="${IDXDIR:?no writable temp dir for the snapshot index}/snap-index-$$"
rm -f "$IDX"
export GIT_INDEX_FILE="$IDX"
trap 'rm -f "$IDX"' EXIT

HEAD_SHA=$(git rev-parse HEAD)
git read-tree HEAD

# Stage every tracked modification plus untracked-but-not-ignored files. Ignored files are
# deliberately excluded: they are build artifacts and caches, and including them would bloat
# the object store on every snapshot.
FILES=$(git ls-files --modified --others --exclude-standard)
if [ -z "$FILES" ]; then
  echo "snapshot: nothing uncommitted in $WT — HEAD $HEAD_SHA already durable"
  exit 0
fi

COUNT=0
DELETED=0
while IFS= read -r f; do
  if [ -L "$f" ]; then
    # Symlink: git stores the TARGET PATH as the blob content under mode 120000. Hashing the
    # file would follow the link and store the wrong thing entirely.
    BLOB=$(printf '%s' "$(readlink "$f")" | git hash-object -w --stdin)
    git update-index --add --cacheinfo "120000,$BLOB,$f"
  elif [ -f "$f" ]; then
    # Preserve the executable bit. Hardcoding 100644 silently strips +x from every script it
    # saves -- this very file is the demonstration case. (Adversarial review, 2026-08-16.)
    if [ -x "$f" ]; then MODE=100755; else MODE=100644; fi
    # --path applies .gitattributes filters (LFS, eol); a bare path can store the wrong blob.
    BLOB=$(git hash-object -w --path "$f" "$f")
    git update-index --add --cacheinfo "$MODE,$BLOB,$f"
  else
    # Tracked but absent => deleted in the working tree. Record the deletion rather than
    # silently keeping HEAD's copy: a snapshot that resurrects deleted files misrepresents the
    # state someone is recovering. (Adversarial review, 2026-08-16.)
    git update-index --force-remove "$f"
    DELETED=$((DELETED + 1))
    continue
  fi
  COUNT=$((COUNT + 1))
done <<< "$FILES"

TREE=$(git write-tree)
PARENT_ARGS=(-p "$HEAD_SHA")
# Chain onto the previous snapshot when one exists, so the ref carries a recoverable history
# rather than a single overwritten tip.
if PREV=$(git rev-parse --verify --quiet "$REF"); then
  PARENT_ARGS+=(-p "$PREV")
fi

COMMIT=$(git commit-tree "$TREE" "${PARENT_ARGS[@]}" \
  -m "snapshot(${NAME}): ${COUNT} file(s), ${DELETED} deletion(s) at ${STAMP}

Automatic durability snapshot. Not a reviewed commit — it exists so that an OOM, reboot, or
worktree deletion cannot destroy uncommitted work. Base HEAD: ${HEAD_SHA}")

git update-ref "$REF" "$COMMIT"
echo "snapshot: ${COUNT} file(s), ${DELETED} deletion(s) -> ${COMMIT} on ${REF}"
echo "  recover: git checkout ${REF} -- <path>   (repo: ${REPO_GIT})"
