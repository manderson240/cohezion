# Session Isolation via Worktrees

## When to Isolate

When the `session-worktree-status.sh` hook reports **ISOLATION RECOMMENDED**:

1. **Before any edits**, ask the user: "You're on a shared branch. Create a worktree for this work?"
2. If yes: derive a slug from the task (e.g., `fix-vote-parsing`, `add-flume-tests`)
3. Run: `cz worktree create --json <slug>`
4. Switch to the worktree directory
5. If no: proceed, but note that changes land on the shared branch

**For `/spec` workflows:** Auto-create worktree without prompting (spec plans always need isolation).

## Branch Naming

Use `feat/<descriptive-slug>` format. The slug should describe the work, not the session:
- `feat/fix-vote-parsing` (good — describes the change)
- `feat/add-cache-warmer-tests` (good — describes the deliverable)
- `session/pid-123456` (bad — meaningless)
- `wip/stuff` (bad — vague)

## Protected Branches (Never Edit Directly)

These patterns are shared/long-lived branches. Edits must go through worktrees:
- `main`, `develop`
- `challenge/*` (competition tracks)
- `release/*` (release candidates)

Read-only operations (Read, Grep, Glob, git log/status/diff) are always allowed.

## Session End

When finishing work on a worktree:
- Suggest `cz worktree sync --json <slug>` to squash-merge back to base
- Suggest `cz worktree cleanup --json <slug>` after successful sync
- Never auto-sync — always get user approval first

## Quick Reference

```bash
cz worktree create --json <slug>    # Create worktree + branch
cz worktree status --json           # Check if in worktree
cz worktree sync --json <slug>      # Squash merge back
cz worktree cleanup --json <slug>   # Remove worktree + branch
```
