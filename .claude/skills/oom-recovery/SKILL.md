---
name: oom-recovery
description: |
  Recover from Claude Code V8 heap OOM crash after large vault sessions.
  Use when: (1) Claude Code process crashes with "FATAL ERROR: Reached heap limit
  Allocation failed - JavaScript heap out of memory", (2) session had 800+ uncommitted
  file changes, (3) continuation files exist from pre-crash sessions. Root cause:
  git status tracking of large uncommitted diffs (deletions from directory migrations)
  creates O(n) memory overhead that accumulates over long sessions.
author: Claude Code
version: 1.0.0
---

# OOM Recovery — Claude Code V8 Heap Exhaustion

## Problem

Claude Code (Node.js/V8) crashes with heap OOM during long vault sessions when the working tree has hundreds of uncommitted file changes. The crash is caused by accumulated memory from:

1. **Git status overhead** — tracking 900+ uncommitted changes (especially mass deletions from directory migrations) creates large in-memory diffs
2. **Context accumulation** — 45+ hour sessions with continuous tool calls compound the V8 heap pressure
3. **Vault graph operations** — reading/writing many markdown files and tracking backlinks multiplies object allocations

**Root cause from this incident**: 978 uncommitted changes (827 deletions from Triune Self directory migration) caused V8 heap to reach limit after ~45 hours.

## Recovery Assessment Steps

Run these immediately after crash to understand what survived:

```bash
# 1. Check current session identity
cz session status --json

# 2. Find ALL continuation files from pre-crash sessions
find ~/.cohezion-engine/sessions/ -name "continuation.md" 2>/dev/null

# 3. Check git state (compact — don't use -uall on large repos)
git status --short | head -30
git status --short | wc -l   # total count
git log --oneline -5          # last commits intact

# 4. Check stash entries survived
git stash list

# 5. Verify specific files from continuation notes exist
ls -la path/to/critical/files
```

## Reading Continuation Files

Old continuation files live in session directories keyed by PID, not the current session:

```bash
# List all session dirs with continuation files
find ~/.cohezion-engine/sessions/ -name "continuation.md" -exec echo {} \;

# Read each — they're in different pid-* directories
cat ~/.cohezion-engine/sessions/pid-37994/continuation.md
cat ~/.cohezion-engine/sessions/pid-3700813/continuation.md
```

**Key**: continuation files reference tasks by ID that don't exist in the new session. Treat them as context documents, not task references.

## Assessing What Actually Completed

The continuation file captures state at handoff time. After the handoff, a session may have continued and completed more work. Always verify:

```bash
# Check if files the continuation said "NOT started" actually exist
ls cortex/*filename*.md 2>/dev/null

# Check line counts to distinguish stubs from real notes
for f in cortex/*toe*.md; do echo "$(wc -l < $f) $f"; done

# Check if MOC updates were done
grep -c "wiki-link-target" cortex/MOC-relevant.md
```

## Preventing Future OOM Crashes

**The #1 prevention**: commit large directory migrations before starting long vault sessions.

```bash
# Before starting a long session, check working tree size
git status --short | wc -l

# If > 200 uncommitted changes, commit first
git add -A  # but check what's being staged first
git status --staged | head -20
# Commit in logical chunks, not one giant commit
```

**Session hygiene**:
- Commit after each major phase (migration, research batch, linking batch)
- Don't let uncommitted changes accumulate across sessions
- If working tree shows > 500 changes, stop and commit before continuing

## Recovery Decision Tree

```
OOM crash detected
    ↓
Run assessment commands (above)
    ↓
Read continuation files from old sessions
    ↓
Verify files that "should exist" on disk
    ↓
Was work actually complete? (file exists + substantial content)
    ├─ YES → Skip re-doing that work, move to next task
    └─ NO  → Resume from continuation "Next Steps"
    ↓
Create fresh task list for current session
    ↓
Prioritize: commit large diff FIRST to prevent next OOM
```

## What Survives an OOM Crash

| Item | Survives? | Notes |
|------|-----------|-------|
| Files written to disk | YES | All markdown notes, code changes |
| Git commits | YES | Committed history is safe |
| Git stash entries | YES | Stash survives process death |
| Continuation files | YES | Written to disk before crash |
| Task list | YES | Persists via `CLAUDE_CODE_TASK_LIST_ID` |
| In-memory tool results | NO | Lost with the process |
| Uncommitted staged changes | YES | Staging area survives |

## Example: This Session's Recovery

- **Crash cause**: 978 uncommitted files (827 deletions from Triune Self migration)
- **Continuation files**: `pid-37994` (code review session) + `pid-3700813` (cosmology notes)
- **Discovery**: cosmology session completed ALL 15 notes + synthesis after the handoff — they existed on disk even though the continuation said "NOT started"
- **Resolution**: Verified via `ls cortex/*cosmology*` + `wc -l` on each file
- **Prevention**: Still need to commit the large migration diff
