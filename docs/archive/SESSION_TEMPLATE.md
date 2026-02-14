# Session XX Startup & Workflow Template

**COPY THIS FILE AT SESSION START** → Save as `SESSION_XX_STARTUP.md` in your worktree

---

## ⚡ Quick Start (5 minutes)

```bash
# 1. Create isolated worktree
SESSION_ID="47"  # Your session number
PHASE="phase-name"  # What you're building
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
- [ ] Reviewed prior session summary
- [ ] Read any blocking docs

**Status**: Ready to work ✅

---

## 🔄 Daily Workflow

### Start of Day
```bash
cd ~/dev/cohezion-session-XX
./scripts/validate-session-setup.sh  # 30 sec
git status  # Ensure clean
```

### During Work
- Make changes, test frequently
- Commit atomically with clear messages

### End of Day
- Full test suite: `uv run pytest tests/ -q`
- If passing, create session summary

---

## 🎯 Session End

Create `SESSION_XX_SUMMARY.md` with accomplishments, test results, and notes for next session.

Final commit with comprehensive message, then push.

---

## 📚 Reference Materials

**Critical** (15 min): CLAUDE.md → MEMORY.md → Prior session summary
**As-Needed**: GIT_WORKTREE_ENFORCEMENT.md, vault decisions/patterns

---

*See full details in SESSION_TEMPLATE.md (in repo)*
