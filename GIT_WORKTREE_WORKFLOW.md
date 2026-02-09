# Git Worktree Workflow for Claude Code Multi-Session Development

**Status**: Foundational workflow documentation for Session 43 and beyond
**Last Updated**: 2026-02-09
**Applies to**: All concurrent Claude Code sessions working on cohezion project

---

## Executive Summary

Git worktrees enable safe, isolated parallel development across multiple Claude Code sessions. Each worktree has its own working directory but shares the same repository history, allowing concurrent work without conflicts.

**Key Benefit**: Eliminates file state conflicts that occur when multiple sessions modify the same working directory simultaneously.

---

## Why Git Worktrees?

### Problem: Shared Working Directory
When multiple Claude Code sessions work in the same `/home/mike-anderson/dev/cohezion` directory:
- Session A modifies `uv.lock`, then pauses
- Session B modifies `main.py`, then pauses
- Session A resumes: now has conflicting state from Session B
- Merge/push operations fail due to untracked files from other sessions
- Git operations become unpredictable

### Solution: Separate Worktrees
Each session gets its own working directory from the same repo:
- Session A works in `/home/mike-anderson/dev/cohezion-session-43/`
- Session B works in `/home/mike-anderson/dev/cohezion-session-44/`
- Each has independent file state, no conflicts
- Each can commit/push independently
- Clean separation of concerns

---

## Quick Start

### Create a Worktree for Your Session

```bash
# From any directory
git worktree add -b <branch-name> ../<worktree-name> main

# Example for Session 43 (FastMCP fix)
git worktree add -b session-43-fastmcp-fix ../cohezion-session-43 main

# Example for Session 44 (Phase 6 continuation)
git worktree add -b session-44-phase-6 ../cohezion-session-44 main
```

**Parameters**:
- `-b <branch-name>`: Create a new branch for this worktree (e.g., `session-43-fastmcp-fix`)
- `../<worktree-name>`: Parent directory and worktree name (sibling to main repo)
- `main`: Branch to check out (usually `main`)

### Work in Your Worktree

```bash
cd ../cohezion-session-43
# Now you're in an isolated working directory
# Make changes, commit, push as normal

git status        # Check changes in THIS worktree only
git add .
git commit -m "..."
git push origin <branch-name>:main
```

### List All Worktrees

```bash
git worktree list
# Output:
# /home/mike-anderson/dev/cohezion             402ea4d1842a [main]
# /home/mike-anderson/dev/cohezion-session-43  402ea4d1842a [session-43-fastmcp-fix]
```

### Clean Up Worktree When Done

```bash
# From main or another worktree
git worktree remove ../cohezion-session-43
# Deletes the worktree directory and branch
```

---

## Workflow: Multi-Session Development

### Before Starting a Session

1. **List existing worktrees** to see what other sessions are active
   ```bash
   git worktree list
   ```

2. **Create your session worktree**
   ```bash
   git worktree add -b session-XX-<task> ../cohezion-session-XX main
   cd ../cohezion-session-XX
   ```

3. **Work in isolation** - all your changes stay in this directory

4. **Push when ready**
   ```bash
   git push origin session-XX-<task>:main
   # Or create a PR if needed
   ```

5. **Clean up when complete**
   ```bash
   cd ../cohezion  # Go to main worktree
   git worktree remove ../cohezion-session-XX
   ```

### Concurrent Sessions Example

**Session 43** (FastMCP fix):
```bash
# In Session 43 terminal
git worktree add -b session-43-fastmcp-fix ../cohezion-session-43 main
cd ../cohezion-session-43
# Make FastMCP fix, commit, push
git push origin session-43-fastmcp-fix:main
git worktree remove ../cohezion-session-43  # Cleanup
```

**Session 44** (Phase 6 work) - runs in parallel:
```bash
# In Session 44 terminal (different window/tab)
git worktree add -b session-44-phase-6 ../cohezion-session-44 main
cd ../cohezion-session-44
# Make Phase 6 changes, commit, push
git push origin session-44-phase-6:main
git worktree remove ../cohezion-session-44  # Cleanup
```

**Result**: No file conflicts, no untracked file issues, clean state for each session

---

## Technical Details

### Git Worktree Architecture

```
~/.../cohezion/                    # Main repo (shared .git directory)
  .git/                            # Shared Git objects, refs, config
  src/
  tests/

~/.../cohezion-session-43/         # Session 43 worktree
  .git -> ../cohezion/.git/worktrees/session-43-fastmcp-fix
  src/                             # Independent working tree
  tests/

~/.../cohezion-session-44/         # Session 44 worktree
  .git -> ../cohezion/.git/worktrees/session-44-phase-6
  src/                             # Independent working tree
  tests/
```

**Key Points**:
- Each worktree's `.git` is a symlink to the main repo's `.git/worktrees/` directory
- All worktrees share the same object database and refs
- No duplication of large files (efficient storage)
- Full git history available in each worktree

### Branch Strategy with Worktrees

Each worktree gets its own branch to prevent conflicts:

```
main (shared reference point)
  ├── session-43-fastmcp-fix (Session 43 worktree)
  ├── session-44-phase-6 (Session 44 worktree)
  └── session-45-optimization (Session 45 worktree)
```

When pushing from a worktree:
```bash
# From session-43-fastmcp-fix worktree
git push origin session-43-fastmcp-fix:main
# Pushes local session-43-fastmcp-fix to remote main
```

---

## Best Practices

### 1. Always Use Descriptive Branch Names
```bash
✅ session-43-fastmcp-fix
✅ session-44-phase-6-analytics
❌ work
❌ test
```

### 2. Fetch Before Pushing
```bash
git fetch origin main
git merge origin/main  # or rebase if needed
git push origin <branch>:main
```

### 3. Keep Worktrees Clean
```bash
# Before cleanup, make sure all changes are pushed
git status                    # Should be "nothing to commit"
git log origin/<branch>..HEAD # Should be empty

# Only then cleanup
git worktree remove ../cohezion-session-XX
```

### 4. Don't Switch Between Worktrees
```bash
❌ DON'T: cd ../cohezion && cd ../cohezion-session-43
✅ DO: Keep each session in its own terminal/window
```

### 5. Use Consistent Naming Convention
```
cohezion-session-<SESSION_NUMBER>-<TASK>
cohezion-session-43-fastmcp-fix
cohezion-session-44-phase-6-analytics
cohezion-session-45-integration-testing
```

---

## Troubleshooting

### "Worktree already exists"
```bash
# Worktree directory exists but git doesn't know about it
git worktree list        # Check if it's still tracked
git worktree remove ../cohezion-session-XX --force  # Remove forcefully
rm -rf ../cohezion-session-XX  # Clean up directory
```

### "Git directory becomes corrupted"
```bash
# Git worktree integrity check
git worktree prune    # Remove stale worktree references
git worktree list     # Verify remaining worktrees
```

### "Can't push due to untracked files from other sessions"
```bash
# Solution: Use a separate worktree
# Never: git clean -fd
# Always: Create a new worktree to avoid shared state
```

### "Worktree checkout fails with 'untracked file' error"
This indicates leftover files from another session. Use a fresh worktree instead of reusing directories.

---

## Integration with Claude Code

### Claude Code Native Support
Claude Code has native support for git worktrees:
- `resume` picker shows sessions from all worktrees in the same repo
- Each worktree can run its own independent Claude session
- Switching between sessions: click a different worktree in the file browser

### Recommended Setup

```bash
# Main development repo
~/.../cohezion/                    # Main worktree, reference point
~/.../cohezion-session-43/         # Session 43 worktree
~/.../cohezion-session-44/         # Session 44 worktree
```

### File Explorer in Claude Code
```
Open folder:
  ☑ /home/mike-anderson/dev/cohezion-session-43

When you resume:
  ✓ Session history from cohezion-session-43 worktree
  ✓ File state from cohezion-session-43 directory
  ✓ No conflicts from other sessions
```

---

## Performance Considerations

### Disk Space
- Multiple worktrees share git objects → minimal overhead
- Only working tree files are duplicated (typically 10-50MB per worktree)
- Large monorepos: multiple worktrees use ~1.5-2x storage vs. single worktree

### Git Operations
- Fetch: same speed (shared object database)
- Commit: same speed (local operations)
- Push: independent per worktree (no waiting)
- Status: slightly faster (fewer untracked files)

### Recommendation for Cohezion
With ~100 files and ~55K lines:
- **Safe to run**: 3-5 concurrent worktrees
- **Memory overhead**: <100MB per worktree
- **Recommended**: 2-3 active sessions, cleanup after completion

---

## Session Workflow Template

Use this template for each new session:

```bash
#!/bin/bash
# Session XX: [Task Description]

SESSION_NUMBER=43
TASK_NAME="fastmcp-fix"
BRANCH_NAME="session-${SESSION_NUMBER}-${TASK_NAME}"
WORKTREE_DIR="../cohezion-session-${SESSION_NUMBER}"

# Create worktree
git worktree add -b ${BRANCH_NAME} ${WORKTREE_DIR} main
cd ${WORKTREE_DIR}

# Work here (Claude Code session)
# ... make changes, test, commit ...

# Push when done
git push origin ${BRANCH_NAME}:main

# Cleanup
cd ../cohezion
git worktree remove ${WORKTREE_DIR}
```

---

## Rationale: Why This Matters for Cohezion

Cohezion uses **compound engineering** with multiple agents working in parallel:
- Agent A (Session 43) fixes FastMCP
- Agent B (Session 44) implements Phase 6 features
- Agent C (Session 45) runs tests in parallel

Without git worktrees:
- ❌ All agents compete for the same `/cohezion/` directory
- ❌ File conflicts (uv.lock, runtime artifacts)
- ❌ Git state becomes unpredictable
- ❌ Push/merge operations fail frequently

With git worktrees:
- ✅ Each agent has isolated working directory
- ✅ No file conflicts, no untracked file issues
- ✅ Clean git state in each worktree
- ✅ Push/merge operations succeed consistently
- ✅ Parallel execution is reliable and safe

---

## References

- [Git Worktrees Documentation](https://git-scm.com/docs/git-worktree)
- [Claude Code Docs: Common Workflows](https://code.claude.com/docs/en/common-workflows)
- [Incident.io: Shipping Faster with Git Worktrees](https://incident.io/blog/shipping-faster-with-git-worktrees)
- [Medium: Mastering Git Worktrees with Claude Code](https://medium.com/@dtunai/mastering-git-worktrees-with-claude-code-for-parallel-development-workflow-41dc91e645fe)

---

## Adoption Checklist

- [ ] All team members read and understand git worktree workflow
- [ ] Create `.claude/workspaces.json` listing active sessions
- [ ] Add worktree cleanup to session exit checklist
- [ ] Document in team onboarding materials
- [ ] Create slack/communication about worktree discipline
- [ ] Set up monitoring for stale worktrees
- [ ] Test multi-session workflow with 3+ concurrent sessions

---

*This document is the foundational workflow for safe, parallel Claude Code development on the Cohezion project. Update this document as we learn more.*
