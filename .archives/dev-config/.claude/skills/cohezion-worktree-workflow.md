---
name: cohezion-worktree-workflow
description: Multi-session worktree workflow for Cohezion development. Covers session scripts (start_session.sh, end_session.sh, list_sessions.sh), manual git worktree commands, commit message format with Co-Authored-By, and recommended git config. Use when starting a new development session, managing worktrees, or committing session work.
---

# Multi-Session Worktree Pattern (MANDATORY)

**Every Claude session MUST start with an isolated worktree.** This is the primary development pattern.

### ⚡ Quick Start (Session Scripts)

```bash
# Start session (interactive or explicit)
./scripts/session/start_session.sh           # Auto-increments session ID
./scripts/session/start_session.sh 56 feature  # Explicit

# List active sessions
./scripts/session/list_sessions.sh

# End session (commit, push, cleanup)
./scripts/session/end_session.sh 56
```

See [`scripts/session/README.md`](scripts/session/README.md) for complete documentation.

### Manual Worktree Commands (Fallback)

```bash
# Create worktree with new branch
git worktree add -b session-56-feature ~/dev/cohezion-session-56 main
cd ~/dev/cohezion-session-56

# Session work: One goal, atomic commits
uv run pytest tests/ -q  # Verify baseline
# ... make changes, test incrementally ...

# Commit with session summary
git commit -m "Session 56: feature

## Accomplishments
- [Deliverables + test count/%, regressions: zero]

## For Session 57
- [Key assumptions, remaining work, gotchas]

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push and cleanup
git push -u origin session-56-feature
cd ~/dev/cohezion && git worktree remove ~/dev/cohezion-session-56
```

**Why**: Isolation → no conflicts | Reversibility → safe branching | Audit trail → clear history | Safety → main never edited directly

**Git Rules** (see `.claude/rules/git-workflow.md`):
- Never force-push to main/develop
- Conventional commits: `feat:`, `fix:`, `test:`, `refactor:`, `chore:`
- AI commits include: `Co-Authored-By: Claude <noreply@anthropic.com>`
- No files >1MB (use git-lfs)
- Check `git status` before any commit

**Recommended Git Config**:
```bash
git config worktree.useRelativePaths true   # Portable worktrees
git config worktree.guessRemote true        # Auto-track remotes
git config gc.worktreePruneExpire 2.weeks.ago
```
