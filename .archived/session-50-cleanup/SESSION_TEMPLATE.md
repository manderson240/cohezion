# Session XX Startup & Workflow Template

**COPY THIS FILE AT SESSION START** → Save as `SESSION_XX_STARTUP.md` in your worktree

---

## ⚡ Quick Start (5 minutes)

```bash
# 1. Create isolated worktree
SESSION_ID="47"  # Your session number
PHASE="phase-name"  # What you're building (e.g., documentation-consolidation)
git worktree add ~/dev/cohezion-session-${SESSION_ID} -b session-${SESSION_ID}-${PHASE}

# 2. Enter worktree
cd ~/dev/cohezion-session-${SESSION_ID}

# 3. Validate setup
./scripts/validate-session-setup.sh
# Expected: Score 5/5 ✅ Ready to work!

# 4. Run baseline tests
uv run pytest tests/compound/ tests/cache/ tests/security/ tests/test_*.py -q
# Expected: 1496 passed, 5 skipped
```

---

## 📋 Session Checklist

- [ ] Created worktree (~/dev/cohezion-session-XX)
- [ ] Checked out feature branch (session-XX-phase-name)
- [ ] Ran validation script (5/5 score)
- [ ] Baseline tests passing (1496/1496)
- [ ] Reviewed prior session summary (MEMORY.md, recent commits)
- [ ] Read any blocking/prerequisite docs

**Status**: Ready to work ✅

---

## 🔄 Daily Workflow

### Start of Day
```bash
cd ~/dev/cohezion-session-XX
./scripts/validate-session-setup.sh  # Quick check (30 sec)
git log --oneline -3  # Verify branch status
git status  # Ensure clean working tree
```

### During Work
```bash
# Make changes, test frequently
uv run pytest tests/compound/ -k "your_feature" -v

# Commit atomically as you complete logical units
git add [related_files]
git commit -m "Clear 1-line summary

## What changed
- Specific feature added
- Bug fixed
- Test coverage improved

## Why this change
- Explains motivation
- References issues if applicable"
```

### End of Day (Before Logging Off)
```bash
# 1. Verify clean state
git status  # Should show "working tree clean"

# 2. Run full test suite
uv run pytest tests/compound/ tests/cache/ tests/security/ tests/test_*.py -q

# 3. If all passing, create summary
# (See "Session End" section below)
```

---

## 🎯 Session End (Before Handoff)

### Final Verification
```bash
# 1. Full test suite
uv run pytest tests/compound/ tests/cache/ tests/security/ tests/test_*.py -q

# 2. Verify all commits are pushed
git log --oneline origin/session-XX-phase-name...HEAD
# Should be empty (all commits pushed)

# 3. Check for untracked files
git status
# Should show: "working tree clean"
```

### Session Summary (Create This Document)

Create `SESSION_XX_SUMMARY.md` with:

```markdown
# Session XX Complete - [PHASE NAME]

**Status**: ✅ COMPLETE | Commits: N | Tests: X/Y passing

## What We Accomplished
- [Key deliverable 1]
- [Key deliverable 2]
- [Test results: X/Y passing (Z%)]

## Verified Metrics
- Tests: X/Y passing
- Regressions: Zero
- Ready for: [production/next-phase]

## For Session XX+1
- [Key assumptions made]
- [Remaining work (if any)]
- [Gotchas to watch for]

## Token Metrics (Optional)
- Budget: XXK tokens
- Actual: XXK tokens
- Variance: ±X% (explanation)
```

### Commit Final Work
```bash
# 1. Create comprehensive final commit
git commit -m "Session XX: PHASE_NAME - COMPLETE ✅

## Accomplishments
- Feature/fix/optimization delivered
- Test coverage: X/Y passing (Z%)

## Verified Metrics
- Tests: X/Y passing
- Regressions: Zero
- Ready for: production/next-phase

## For Session XX+1
- [Key assumptions]
- [Remaining work]
- [Gotchas]"

# 2. Push to remote
git push origin session-${SESSION_ID}-${PHASE}

# 3. Return to main directory
cd ~/dev/cohezion

# 4. Update MEMORY.md with summary
# (See Phase A: Documentation Consolidation task)
```

### Cleanup Worktree (Optional - Only If Session Complete)
```bash
# ONLY do this when fully confident work is done and pushed
git worktree remove ~/dev/cohezion-session-${SESSION_ID}

# Verify main is clean
cd ~/dev/cohezion
git status  # Should show "working tree clean"
```

---

## 📚 Reference Materials (Read Once Per Session)

**Critical Reading** (15 minutes):
1. CLAUDE.md - Project directives & coding standards
2. MEMORY.md - Current project state & architecture
3. Prior session summary - What was accomplished last time
4. git log -5 --oneline - Recent commits to understand context

**As-Needed Reference** (When solving specific problems):
- `GIT_WORKTREE_ENFORCEMENT.md` - Git workflow troubleshooting
- `/vaults/cohezion-vault/decisions/` - Architecture decisions (search by phase or topic)
- `/vaults/cohezion-vault/patterns/` - Reusable patterns from prior sessions
- Test files - Best code examples for your domain

---

## ✅ Success Criteria for Session

Every session should deliver:
1. **Code Quality**: All tests passing (0 regressions)
2. **Documentation**: Session summary + commit messages
3. **Clean State**: Working tree clean, all commits pushed
4. **Knowledge Transfer**: Notes for next session in MEMORY.md or vault

---

## 🆘 Troubleshooting

**Worktree issues?** → See `GIT_WORKTREE_ENFORCEMENT.md`

**Test failures?** → Check if:
- Pre-existing failures (read Session X summary)
- Import cycles (check `src/cohezion/*/` has `__init__.py`)
- Timing issues (run with `-v` to debug)

**Git conflicts?** → Never use git worktree pattern wrong
- Always work in ~/dev/cohezion-session-XX
- Never commit directly to main
- Push to feature branch only

**Context questions?** → Ask:
1. CLAUDE.md (project rules)
2. MEMORY.md (state + architecture)
3. Recent commits (git log -10)
4. Vault decisions (search topic)

---

## 🚀 Template Lifecycle

- **Copy this file** at start of every session
- **Update for your session** (replace "XX", "phase-name", etc.)
- **Follow it** throughout the day
- **Complete the checklist** before handoff
- **Archive** in project if useful pattern emerges

This template enables **compound engineering**: Each session follows the same pattern, making infrastructure consistent and token-efficient across all sessions.

---

*Last Updated: Session 46 (2026-02-09)*
*Pattern: Git Worktree + Feature Branches + Atomic Commits + Session Summaries*
