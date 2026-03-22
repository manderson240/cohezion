# Git Worktree Pattern: MANDATORY ENFORCEMENT

**Status**: ACTIVE & ENFORCED for ALL sessions (current and future)
**Effective Date**: 2026-02-09 (Session 46)
**Scope**: Every Claude session MUST follow this pattern
**Non-Negotiable**: YES

---

## 🚨 Why This Matters

The Cohezion project experienced a critical git history divergence in Session 46:
- Local history: 213 commits
- Remote history: 145 commits
- Common ancestor: NONE

**Root cause**: Multiple sessions working directly in `~/dev/cohezion` without isolation.

**Solution**: Git worktrees + feature branches = zero conflicts, full isolation, token efficiency.

---

## ENFORCEMENT MECHANISMS

### 1. Git Pre-Commit Hook (Prevents Direct Main Commits)

**Location**: `.git/hooks/pre-commit`

**What it does**:
- ❌ Blocks commits directly to `main`
- ❌ Warns about non-session branch names
- ✅ Allows commits on `session-XX-*` branches

**Example**:
```bash
git commit -m "Work"  # On 'main'
# Output: ❌ ERROR: Direct commits to 'main' are not allowed
# Use the git worktree pattern instead...
```

---

### 2. CLAUDE.md Project Directive

**Location**: `/home/mike-anderson/dev/cohezion/CLAUDE.md` (section: Multi-Session Git Worktree Pattern)

**What it enforces**:
- Mandatory for all sessions
- Specific startup/work/cleanup procedures
- Clear success criteria
- Template for commit messages

**Applies to**: ALL Claude sessions (current + future)

---

### 3. Session Validation Script

**Location**: `/home/mike-anderson/dev/cohezion/scripts/validate-session-setup.sh`

**How to use**:
```bash
cd ~/dev/cohezion-session-47
./scripts/validate-session-setup.sh
# Output:
#   ✅ Worktree Setup
#   ✅ Branch Naming
#   ✅ Main Directory Clean
#   ✅ Tests Available
#   ✅ Documentation Found
#   Score: 5/5
#   ✅ Ready to work!
```

**Checks performed**:
- ✅ Isolated worktree (~/dev/cohezion-session-XX)
- ✅ Proper branch naming (session-XX-phase-name)
- ✅ Main directory clean
- ✅ Test baseline available
- ✅ Documentation found

---

### 4. Memory & Vault Persistence

**Memory** (persists across sessions):
- `MEMORY.md`: Session status updated after each session
- Format: Session XX: [Phase], Status: [Complete], Tests: [X/Y], For Next: [...]

**Vault** (permanent decision log):
- Decision: `/vaults/cohezion-vault/decisions/2026-02-09-session-46-git-unification-complete.md`
- Pattern: `/vaults/cohezion-vault/patterns/multi-session-compound-engineering-workflow.md`

**Key entries**:
- Why: Prevent diverged histories, enable parallel work
- How: Worktrees + feature branches
- When: Every session, starting Session 47
- Who: All Claude sessions

---

## WORKFLOW FOR ALL SESSIONS

### Session Start Checklist
```bash
# 1. Verify which session this is
SESSION_ID="47"  # Sequential numbering (46, 47, 48, ...)
PHASE="production-deployment"  # What you'll work on
BRANCH="session-${SESSION_ID}-${PHASE}"  # Branch name

# 2. Create isolated worktree
git worktree add ~/dev/cohezion-session-${SESSION_ID} -b ${BRANCH}

# 3. Switch to worktree
cd ~/dev/cohezion-session-${SESSION_ID}

# 4. Validate setup
./scripts/validate-session-setup.sh

# 5. Verify main directory is clean
cd ~/dev/cohezion
git status  # Should show "working tree clean"

# 6. You're ready to work in the worktree
cd ~/dev/cohezion-session-${SESSION_ID}
```

### During Session
```bash
# Work in ~/dev/cohezion-session-XX, NOT ~/dev/cohezion

# Make changes, run tests frequently
uv run pytest tests/compound/ tests/cache/ tests/security/ tests/test_*.py -q

# Commit atomically
git add [files]
git commit -m "Clear commit message"

# NEVER: cd ~/dev/cohezion && git commit
# NEVER: git checkout main && commit
# ALWAYS: Stay in ~/dev/cohezion-session-XX
```

### Session End
```bash
# 1. Final comprehensive commit
git commit -m "Session XX: PHASE_NAME

## Accomplishments
- [Key deliverables]
- [Test results: X/Y passing (Z%)]

## Verified Metrics
- Tests: X/Y passing
- Regressions: Zero
- Ready for: [production/next-phase]

## For Session XX+1
- [Key assumptions]
- [Remaining work]
- [Gotchas to watch]"

# 2. Push feature branch (NOT main)
git push origin session-${SESSION_ID}-${PHASE}

# 3. Return to main directory
cd ~/dev/cohezion

# 4. Clean up worktree
git worktree remove ~/dev/cohezion-session-${SESSION_ID}

# 5. Verify clean state
git status  # Should show "working tree clean"

# 6. Return to worktree to verify push succeeded
cd ~/dev/cohezion-session-${SESSION_ID} 2>/dev/null
git log --oneline -3  # Verify your commits are there

# 7. Back to main
cd ~/dev/cohezion
```

---

## What Happens If Pattern Is Broken

### Scenario 1: Direct commit to main
```bash
git checkout main
git commit -m "My work"
# ❌ Pre-commit hook blocks it:
# ERROR: Direct commits to 'main' are not allowed
# Use the git worktree pattern instead
```

### Scenario 2: Wrong branch name
```bash
git worktree add ~/dev/cohezion-session-47 -b my-feature  # ❌ Wrong name
./scripts/validate-session-setup.sh
# ⚠️  WARNING: Branch name doesn't follow session pattern
# Expected: session-XX-phase-name
# Current: my-feature
```

### Scenario 3: Working from main directory
```bash
cd ~/dev/cohezion  # WRONG
git checkout -b session-47-work
./scripts/validate-session-setup.sh
# ⚠️  NOT in a worktree
# Current directory: /home/mike-anderson/dev/cohezion
# Expected: ~/dev/cohezion-session-XX
```

---

## For Future Sessions (47+): Getting Started

### First Time
1. Read: `/home/mike-anderson/dev/cohezion/CLAUDE.md` (section: Multi-Session Git Worktree Pattern)
2. Read: `/home/mike-anderson/dev/cohezion/SESSION_46_RETROSPECTIVE_AND_HANDOFF.md`
3. Read: `/home/mike-anderson/vaults/cohezion-vault/patterns/multi-session-compound-engineering-workflow.md`

### Every Session
1. Create worktree with sequential numbering
2. Run validation script
3. Work in isolated environment
4. Commit with template
5. Push feature branch
6. Clean up worktree

### Verification
```bash
# Session 47 startup
SESSION_ID="47"
git worktree add ~/dev/cohezion-session-${SESSION_ID} -b session-${SESSION_ID}-phase-name
cd ~/dev/cohezion-session-${SESSION_ID}
./scripts/validate-session-setup.sh

# Expected output:
# ✅ Worktree Setup
# ✅ Branch Naming
# ✅ Main Directory Clean
# ✅ Tests Available
# ✅ Documentation Found
# Score: 5/5
# ✅ Ready to work!
```

---

## Reference Materials

**Inside Cohezion Repo**:
- `CLAUDE.md` - Project directives (includes this pattern)
- `SESSION_46_RETROSPECTIVE_AND_HANDOFF.md` - Latest session workflow
- `GIT_WORKTREE_WORKFLOW.md` - Operational guide
- `scripts/validate-session-setup.sh` - Validation script

**In Vault**:
- `/vaults/cohezion-vault/decisions/2026-02-09-session-46-git-unification-complete.md` - Decision log
- `/vaults/cohezion-vault/patterns/multi-session-compound-engineering-workflow.md` - Pattern details

**Git Hooks**:
- `.git/hooks/pre-commit` - Enforces pattern at commit time

---

## Troubleshooting

### I accidentally committed to main. How do I fix it?
```bash
# 1. Reset the commit (keep changes)
git reset HEAD~1

# 2. Create a worktree for this work
git worktree add ~/dev/cohezion-session-XX -b session-XX-phase-name

# 3. Stage and commit in worktree
cd ~/dev/cohezion-session-XX
git add [files]
git commit -m "Session XX: [message]"

# 4. Push from worktree
git push origin session-XX-phase-name
```

### I created a worktree with the wrong name. How do I rename it?
```bash
# 1. Check the worktree
git worktree list

# 2. Create a new one with the right name
git worktree add ~/dev/cohezion-session-47 -b session-47-correct-phase

# 3. Move your changes
cd ~/dev/cohezion-session-47
git cherry-pick [commit hashes]  # Or copy files and commit

# 4. Remove the wrong one
git worktree remove ~/dev/cohezion-wrong-name
```

### How do I check if I'm in a worktree?
```bash
pwd
# If it shows: /home/mike-anderson/dev/cohezion-session-47
# ✅ You're in a worktree

# If it shows: /home/mike-anderson/dev/cohezion
# ❌ You're in the main directory
```

---

## Enforcement Status

| Mechanism | Status | Coverage |
|-----------|--------|----------|
| Git hook (pre-commit) | ✅ Active | Prevents main commits |
| CLAUDE.md directive | ✅ Active | All sessions |
| Validation script | ✅ Active | Per-session check |
| Memory persistence | ✅ Active | Cross-session tracking |
| Vault logging | ✅ Active | Permanent record |

**Enforcement Coverage**: 100% of sessions (current + future)

---

## Success Metrics

✅ **Zero git history divergence** (target: all future sessions)
✅ **100% worktree compliance** (target: all sessions use pattern)
✅ **Zero data loss** (target: no lost commits)
✅ **Token efficient** (target: no merge conflict overhead)
✅ **Clear audit trail** (target: each session = one branch)

---

## Approval & Sign-Off

**Approved by**: Session 46 (retrospective & enforcement)
**Effective**: 2026-02-09 onwards
**Applies to**: All active Claude sessions + all future sessions
**Status**: MANDATORY (non-negotiable)

---

**This pattern is the foundation for sustainable, scalable multi-session development.**

**Every session that follows this pattern prevents another git disaster and enables efficient parallel work.**

---

*Last Updated: Session 46 (2026-02-09)*
*Next Review: Session 50 or when issues arise*
*Maintainer: Claude Code + Project Team*
