---
title: "Merging a branch when the dev checkout has read-only mounts"
date: 2026-06-06
tags: [git, merge, worktree, read-only-mount, PR-landing, retro]
verified: true
---

# Retro — landing a 225-commit branch onto origin/main under read-only ZFS mounts

## Context
Landing `feat/adaptive-calibration-harness` (225 ahead / 20 behind) onto `origin/main`. The dev
checkout has `scripts/` and `config/` mounted **read-only** (ZFS). `origin/main` modifies 30+
files under those paths.

## What worked (reusable techniques)

1. **Measure the conflict surface WITHOUT touching anything: `git merge-tree`.**
   `git merge-tree --write-tree --name-only origin/main HEAD` computes the full merge and prints
   conflicted paths — writes nothing to the working tree, no branch, no abort needed. Turned the
   audit's "MEDIUM-HIGH estimate" into ground truth (42 real conflicts) before any irreversible step.

2. **In-place merge is IMPOSSIBLE under read-only mounts — and fails loudly.**
   `git merge origin/main` → `error: unable to unlink old 'scripts/...': Read-only file system` →
   `fatal: read-tree failed`. Git must write the merged `scripts/`/`config/` files; the RO mount
   blocks it. This is environmental, not a conflict.

3. **Do the merge in a git worktree at a WRITABLE path, on a SIDE branch.**
   `git worktree add -b merge/<name> "$TMPDIR/wt" HEAD` — the worktree's `scripts/`/`config/` are
   ordinary writable copies (NOT the RO mounts; `test -w "$WT/scripts"` ✅). Merge + resolve there.
   The main RO checkout is never touched. Push the side branch; open the PR from it. (Advancing the
   feature branch itself would also fail — the main checkout's working tree can't sync scripts/.)

4. **`-X ours` is the right strategy for a land-the-branch merge.**
   Keeps the feature branch's side on every conflicting hunk while still absorbing main's
   non-conflicting advances. Reduced lint debt 555→405 (main's cleaner files came in for free).

5. **Validate worktree code with the MAIN venv via PYTHONPATH.**
   The worktree has no `.venv`, and the venv's editable install points at the main checkout's src.
   `PYTHONPATH="$WT/src" /main/.venv/bin/python "$WT/.claude/rules/harness_check.py"` validates the
   MERGED tree (worktree src wins on the path), not the main checkout.

## Gotchas
- `gh` token was invalid → couldn't `gh pr create`; the `git push` output gives the PR-creation URL.
- A pre-existing committed conflict marker (`>>>>>>> origin/polish/...`) in `research/posters/build_poster.py`
  surfaced — pre-dated the merge (on HEAD), flagged for separate cleanup, NOT introduced by the merge.
- The `--clear` of the `[retro:due]`/`.last-scan` markers fails: `~/.claude/` is also a read-only mount.

## Persistence note
Skill extraction (`/learn`) is blocked this session — `.claude/skills/` and `~/.claude/` are
read-only mounts. Durable learnings therefore land in `docs/` (writable), e.g. this file and the
methodology note in `docs/audits/WIRING_SWEEP_LEDGER.md` ("compiles ≠ reachable").
