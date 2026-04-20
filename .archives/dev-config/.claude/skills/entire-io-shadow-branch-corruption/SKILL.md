---
name: entire-io-shadow-branch-corruption
description: |
  Fix for Entire.io "carry forward" creating corrupted git trees with empty filenames.
  Use when: (1) git bundle create --all fails with "empty filename in tree entry",
  (2) git fsck shows badTree errors, (3) entire/ shadow branches accumulate >500.
triggers:
  - "empty filename in tree entry"
  - "badTree"
  - "pack-objects died"
  - "entire shadow branches"
  - "git bundle fail"
---

# Entire.io Shadow Branch Corruption

## Symptom

```
fatal: empty filename in tree entry
error: pack-objects died
```

This breaks `git bundle create --all`, `git push --all`, and any tool that traverses all refs (e.g., ultraplan session creation).

## Root Cause

Entire.io's "carry forward: uncommitted session files" creates orphan commits with absolute filesystem paths when it tracks files **outside the repo root** (e.g., `~/.claude/plans/`).

In git's tree format, an absolute path `/home/user/.claude/plans/` becomes:
```
"" (empty name = /) → home → user → .claude → plans
```

The empty-name tree entry is illegal and causes hard parse failures.

## Diagnosis

```bash
# 1. Confirm the corruption
git fsck --full 2>&1 | grep "badTree" | wc -l

# 2. Find which branches are affected
git branch --all --contains <bad-commit-hash>

# 3. Inspect the bad tree
python3 -c "
import subprocess
raw = subprocess.check_output(['git', 'cat-file', 'tree', '<tree-hash>'], stderr=subprocess.DEVNULL)
i = 0
while i < len(raw):
    null_pos = raw.index(b'\x00', i)
    header = raw[i:null_pos]
    sp = header.index(ord(b' '))
    name = header[sp+1:].decode('utf-8', errors='replace')
    sha = raw[null_pos+1:null_pos+21].hex()
    if len(name) == 0:
        print(f'EMPTY NAME entry -> {sha}')
    i = null_pos + 21
"
```

## Fix

```bash
# 1. Delete the corrupted branch (if isolated)
git branch -D entire/<hash>

# 2. Use Entire's own cleanup for orphaned branches
entire clean --all --dry-run   # preview
entire clean --all --force     # execute

# 3. GC to remove unreachable objects
git reflog expire --expire=now --all
git gc --prune=now

# 4. Verify
git fsck 2>&1 | grep "badTree"  # should return nothing
git bundle create /tmp/test.bundle --all  # should succeed
rm /tmp/test.bundle
```

## Prevention

- **Entire strategy:** Use `manual-commit` (not auto-commit) to avoid carry-forward of uncommitted files
- **Monitor branch count:** `git branch | grep "entire/" | wc -l` — flag if >200
- **Periodic cleanup:** Run `entire clean --all --dry-run` monthly

## Key Facts

- `transfer.fsckObjects=false` does NOT bypass this — the empty-filename check is a hard parse error in git's tree reader, not a configurable fsck check
- Only objects reachable from refs cause bundle failures — unreachable bad trees are harmless
- `entire/checkpoints/v1` is preserved by `entire clean` — it's the main checkpoint branch
- Entire.io v0.5.3 (April 2026) has this bug in carry-forward; no config to prevent it

## Anti-Patterns Discovered

1. **Absolute path in git tree:** Entire.io resolved paths to absolute form instead of making them relative to repo root
2. **Shadow branch accumulation:** 1,048 branches accumulated over ~5 weeks without cleanup
3. **Orphan commits:** "carry forward" creates root commits (no parent) — these are never reachable from main history
