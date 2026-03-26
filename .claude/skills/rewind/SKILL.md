---
name: rewind
description: Browse and rewind to Entire.io checkpoints with full agent context.
  Use when you need to go back to a prior state, understand what happened in a
  previous session, or recover lost reasoning context.
---

# Rewind to Checkpoint

Browse Entire.io checkpoints and rewind your session state.

## Step 1: List Available Checkpoints

```bash
entire explain --short 2>/dev/null | head -30
```

Present the checkpoints to the user as a numbered list showing:
- Checkpoint ID
- Timestamp
- Intent/description
- Commits associated

## Step 2: User Selects Checkpoint

Ask the user which checkpoint they want to rewind to or explain.

## Step 3: Explain or Rewind

### To understand what happened at a checkpoint:
```bash
entire explain -c <checkpoint_id>
```

### To rewind to a checkpoint (restores code + agent context):
```bash
entire rewind --to <commit_id>
```

**Warning:** Rewind modifies the working directory. Confirm with the user before executing.

## Step 4: Verify State

After rewind:
1. `git log --oneline -3` — confirm HEAD is at expected commit
2. `git status` — check working tree is clean
3. `entire status` — verify session state

## When NOT to Rewind

- If you just need context, use `entire explain` instead
- If the user has uncommitted changes, warn them first
- If the checkpoint is from a different branch, warn about branch implications
