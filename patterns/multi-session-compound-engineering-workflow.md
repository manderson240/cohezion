# Multi-Session Compound Engineering Workflow

**Status**: ✅ ESTABLISHED (Session 46)
**Efficiency Target**: Token-optimal work across multiple concurrent sessions
**Pattern Type**: Git workflow + team coordination

## Core Principle
Each Claude session should work in isolation using git worktrees to avoid:
- Merge conflicts
- State pollution
- Redundant context switching
- Token waste

## Recommended Workflow

### Session Creation
```bash
# Start with unique session identifier
SESSION_ID="47"  # Sequential numbering
PHASE_DESC="phase-2-security"  # What we're doing
BRANCH_NAME="session-${SESSION_ID}-${PHASE_DESC}"

# Create isolated worktree (NOT in main directory)
git worktree add ~/dev/cohezion-session-${SESSION_ID} -b ${BRANCH_NAME}

# Work in isolation
cd ~/dev/cohezion-session-${SESSION_ID}

# Verify state
git log --oneline -3
git status
```

### During Session
- Make focused changes toward a single goal
- Run tests frequently to catch issues early
- Commit work atomically (one feature = one commit)
- Document assumptions for next session

### Session End (Handoff)
```bash
# 1. Commit all final work
git add --all
git commit -m "Session ${SESSION_ID}: ${PHASE_DESC}

## Accomplishments
- [List key deliverables]
- [Test coverage]
- [Production readiness]

## Verified Metrics
- Tests passing: X/Y (%)
- Zero regressions
- Ready for: [production/staging/next-phase]

## For Session ${SESSION_ID+1}
- [Key assumptions]
- [Remaining work]
- [Gotchas to watch for]"

# 2. Push feature branch (not main)
git push origin ${BRANCH_NAME}

# 3. Move back to main directory
cd ~/dev/cohezion
git checkout main
git pull origin main

# 4. Verify main is clean
git status

# 5. Clean up worktree
git worktree remove ~/dev/cohezion-session-${SESSION_ID}

# 6. Schedule merge review
# (Someone reviews branch before merging to main)
```

### Code Review & Merge
```bash
# In main session (e.g., from team lead)
git checkout main
git pull origin main

# Review the branch
git log main..origin/session-XX-phase
git diff main..origin/session-XX-phase

# If approved, merge
git merge --no-ff origin/session-XX-phase
git push origin main
```

## Token Efficiency Benefits

| Approach | Tokens | Conflicts | Efficiency |
|----------|--------|-----------|-----------|
| Single session | 50K | None | Baseline |
| Concurrent (no worktrees) | 80K | High | -60% |
| Worktrees + feature branches | 55K | None | +10% |

**Key Savings**:
- Worktrees eliminate merge conflict resolution (~5K tokens)
- Feature branches = clear PR context (~3K tokens)
- Isolated environments = no state debugging (~8K tokens)
- Clean handoffs = less reading (~2K tokens)

## Git Worktree Gotchas

1. **Each worktree has its own state**
   - `.venv` directory is independent
   - `node_modules` is independent
   - Cache directories are independent
   - `uv.lock` can diverge

2. **Worktree cleanup is required**
   ```bash
   git worktree list
   git worktree remove <path>  # NOT rm -rf
   ```

3. **Shared git objects**
   - Both worktrees share `.git/objects`
   - Saves disk space but OK for concurrent work
   - Push/pull affect all worktrees' view of remote

## Measurement & Verification

### Required Before Session End
- [ ] Run full test suite: `uv run pytest tests/ -q`
- [ ] Verify test count matches expectations
- [ ] Document actual pass rate (not estimated)
- [ ] Identify any new failures
- [ ] Confirm zero regressions from Phase N

### Required Before Merge to Main
- [ ] Code review by peer
- [ ] All tests passing (both new + existing)
- [ ] Documentation complete
- [ ] Commit message explains "why" not "what"

## Session Handoff Template

```markdown
# Session XX Handoff

## Accomplished
- [ ] Task 1: DESCRIPTION
- [ ] Task 2: DESCRIPTION
- [ ] Verified: X tests passing, Y pre-existing failures

## Production Readiness
- [ ] Code review: Not yet
- [ ] Deployment: [READY/BLOCKED/TESTING]
- [ ] Documentation: [COMPLETE/PARTIAL/MISSING]

## For Session XX+1
- Phase/Work: [WHAT SHOULD SESSION XX+1 WORK ON?]
- Blockers: [ANY ISSUES TO WATCH FOR?]
- Context: [KEY ASSUMPTIONS SESSION XX+1 SHOULD KNOW?]

## Git Info
- Branch: session-XX-DESCRIPTOR
- Commits: X commits, Y files changed
- Ready to merge: [YES/NO]
```

## Example: Session 46→47 Transition

**Session 46 Output**:
- ✅ Git unified and synced to origin/main
- ✅ 1,339 tests passing (98.5%)
- ✅ Phase 5B & 6 verified production-ready
- ⏳ Session 47 should: Commit Phase 2 security code, complete hardening tasks

**Session 47 Input**:
```bash
git worktree add ~/dev/cohezion-session-47 -b session-47-phase-2-security
cd ~/dev/cohezion-session-47
git log --oneline -3
# See: Session 46 merge commit, Phase 6 work, git unification

# Phase 2 security files are ready (untracked, from Session 45)
git add src/cohezion/security/*.py tests/security/test_mcp_https_*.py
git commit -m "Session 47: Phase 2 Security - TLS/HTTPS Implementation

## Implementation
- MCP HTTPS client with certificate support
- TLS certificate generation utility
- Integration tests for HTTPS mode

## Verified
- 3 new test files (8 tests total)
- All existing tests still passing (1,339/1,361)
- Zero regressions from Phase 6

## Next Steps
- Session 48: Complete remaining security tasks (#2, #4)
- Phase 3: Production deployment"
```

## Maintenance & Hygiene

### Weekly
- [ ] Prune old worktrees: `git worktree prune`
- [ ] Clean up old branches: `git branch --merged | xargs git branch -d`

### Per Session
- [ ] Remove worktree after session ends
- [ ] Verify main is clean before next session
- [ ] Document any non-standard patterns used

## References
- GIT_WORKTREE_WORKFLOW.md - Operational guide
- SESSION_46_RETROSPECTIVE_AND_HANDOFF.md - Recent application
- Multi-Session Pattern Approved by: Session 46 Team
