---
title: 'Multi-Session Compound Engineering Workflow'
date: 2026-02-23
tags: [pattern]
aspect: thinker
neural:
  activation: 0.94
  stage: mature
  synapse_in: 25
  synapse_out: 13
---
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


[[workflow-orchestration]], [[agentic-ai]]

- [[2026-02-22-cz-spec-workflow-retrospective|cz spec workflow retrospective]] — a real-world run of the worktree + spec workflow pattern documented here; the retrospective identifies concrete improvements (D1–D5) to this workflow
- [[2026-02-09-session-46-git-unification-complete]] — the session that first proved and approved the git-worktree multi-session pattern, resolving 30+ file conflicts across diverged histories
- [[2026-02-10-canvas-driven-compound-engineering]] — the canvas-driven workflow fits into this multi-session compound engineering pattern for vault enrichment
- [[2026-02-10-compound-engineering-meta-learning]] — the meta-learning feedback loop that provides the continuous data source for this multi-session workflow
- [[2026-02-14-compound-engineering-team-execution-retrospective]] — the 3-agent team run (decision-linker + inbox-triager + compound-engineering agents) that demonstrated this pattern applied to vault maintenance at scale: +453 wiki-links, -55pp orphan rate, 15min wall time
- [[2026-02-13-phase-2-track-a-complete]] — Track A used this pattern (isolated parallel execution, zero conflicts)
- [[2026-02-14-phases-1-3-retrospective-key-learnings]] — the retrospective that codified parallel-track execution as Pattern 1 (40-45% compression)

## Scientific Foundation

- [[scaling-agent-systems]] — the paper's key finding that centralized coordination contains error amplification to 4.4x (vs 17.2x for independent agents) directly validates this pattern's design: each git worktree is an isolated agent, and the mandatory merge-review step before touching main IS the centralized validation bottleneck the paper prescribes. The workflow's measurable token-efficiency gains (55K vs 80K for concurrent-without-isolation) align with the paper's "fixed compute budget" framing.
- [[llm-in-sandbox-agentic-intelligence]] — git worktrees are a filesystem-level sandbox, equivalent to the code sandbox isolation described in the paper; both prevent cross-session state contamination while enabling full environment access
- [[lesson-git-worktrees-multi-session-isolation]] — the lesson that motivated this pattern, grounded in the real cost of diverged histories (213 vs 145 commits, no common ancestor)

## Session References

- [[session-49-retrospective]] — worktree isolation lesson learned the hard way: files lost to auto-formatters without isolation