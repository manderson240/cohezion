# Phase 5B Quick Start Guide

**Read this first!** (5 minutes)

---

## What You Need to Know

You are working on **Phase 5B: Multi-Agent Coordination** of the Cohezion project.

The git repository is ready for team work. All Phase 5B code is complete and waiting to be committed as atomic subsystems.

**Current status**: feature/token-efficiency-5b branch is clean with:
- 892 tests passing ✓
- 2 files modified (cache + cost_opt exports)
- 144 untracked files (all Phase 5B implementation)
- Ready for team execution

---

## 5-Minute Onboarding

### 1. Understand the Branch (2 min)
Read: **GIT_STATE_SNAPSHOT.txt**
- What commit you're on
- How many commits ahead of remote
- What tests are passing
- What untracked files exist

### 2. Know Your Subsystem (2 min)
Find your name in the list below, then go to step 3.

### 3. Get Your Checklist (1 min)
Open: **PHASE_5B_COMMIT_CHECKLIST.md**
Find your subsystem section.
That's your execution guide.

---

## Which Subsystem Are You Working On?

### redis-specialist → 5B.1: Redis Semantic Cache
**Go to**: PHASE_5B_COMMIT_CHECKLIST.md → "Subsystem 1: Redis Semantic Cache"
- **Time**: 4-5 hours
- **Files**: redis_cache.py + tests (2 files)
- **Ready?**: Implementation waiting for tests to pass
- **Copy/Paste Command**: Provided in checklist

### consensus-engineer → 5B.2: Consensus Skill Voting
**Go to**: PHASE_5B_COMMIT_CHECKLIST.md → "Subsystem 2: Consensus Skill Voting"
- **Time**: 3-4 hours
- **Files**: skill_consensus_voter.py (1 file - tests already committed)
- **Ready?**: Tests already committed, implement the class
- **Copy/Paste Command**: Provided in checklist

### dashboard-engineer → 5B.3: Global Metrics Aggregation
**Go to**: PHASE_5B_COMMIT_CHECKLIST.md → "Subsystem 3: Global Metrics Aggregation"
- **Time**: 3-4 hours
- **Files**: global_metrics_aggregator.py + tests (2 files)
- **Ready?**: Implementation ready
- **Copy/Paste Command**: Provided in checklist

### session-specialist → 5B.4: Session Persistence
**Go to**: PHASE_5B_COMMIT_CHECKLIST.md → "Subsystem 4: Session Persistence"
- **Time**: 3-4 hours
- **Files**: session_manager_persistence.py + tests (3 files)
- **Ready?**: Implementation ready
- **Copy/Paste Command**: Provided in checklist

### cost-optimizer → 5B.5: Cost-Aware Router
**Go to**: PHASE_5B_COMMIT_CHECKLIST.md → "Subsystem 5: Cost-Aware Router"
- **Time**: 4-5 hours
- **Files**: cost_aware_router.py + tests (2 files)
- **Ready?**: Implementation ready
- **Copy/Paste Command**: Provided in checklist

### qa-lead → 5B.6: Integration Testing
**Go to**: PHASE_5B_COMMIT_CHECKLIST.md → "Subsystem 6: Integration Testing"
- **Time**: 3-4 hours
- **Files**: test_phase_5b_integration.py (1 file)
- **Ready?**: Tests ready to finalize
- **Copy/Paste Command**: Provided in checklist

### All Team Members → 5B.7: Documentation & Decisions
**Go to**: PHASE_5B_COMMIT_CHECKLIST.md → "Subsystem 7: Documentation & Decisions"
- **Time**: 1-2 hours (shared)
- **Files**: Vault decisions + docs
- **Copy/Paste Command**: Provided in checklist

---

## Step-by-Step Workflow

### 1. You Start Work
```bash
# Verify you're on the right branch
git status
# Expected: "On branch feature/token-efficiency-5b"

# Pull latest changes
git pull origin feature/token-efficiency-5b
```

### 2. You Implement Your Subsystem
- Write code in your assigned files
- Write tests (100% coverage required)
- Test locally: `uv run pytest tests/ -q`
- Format code: `ruff format src/`

### 3. Before You Commit
Open **PHASE_5B_COMMIT_CHECKLIST.md** and find your subsystem section.

Go through each checklist item:
- [ ] Implementation complete
- [ ] Tests written and passing
- [ ] 100% coverage verified
- [ ] Backward compatibility check
- [ ] Imports verified
- [ ] Documentation complete
- [ ] Vault decision logged
- [ ] Ready to commit

### 4. You Commit
Copy the commit command from your section of the checklist.
```bash
git add <your files>
git commit -m "<message from checklist>"
```

### 5. You Push
```bash
git push origin feature/token-efficiency-5b
```

### 6. Repeat for Your Subsystem
(If your subsystem has multiple commits)

---

## Important Rules

### ✅ DO
- ✅ Follow your subsystem checklist
- ✅ Run all tests before committing
- ✅ Use the exact commit message format provided
- ✅ Push to feature/token-efficiency-5b (not main/develop)
- ✅ Ask for help if blocked

### ❌ DON'T
- ❌ Force-push to any branch
- ❌ Delete untracked files
- ❌ Skip tests or code review
- ❌ Change existing APIs without approval
- ❌ Commit directly to main or develop

---

## If You Get Stuck

### Tests Failing?
1. Read error message carefully
2. Check PHASE_5B_IMPLEMENTATION_GUIDE.md for patterns
3. Look at existing tests in tests/ directory
4. Ask team-lead for help

### Import Errors?
1. Verify __init__.py exports (look at modified __init__.py files)
2. Check for circular imports (run test to verify)
3. Reference PHASE_5B_IMPLEMENTATION_GUIDE.md

### Git Confused?
1. Read GIT_WORKFLOW_PHASE_5B.md for detailed procedures
2. Don't panic - git is very hard to break
3. Ask devops-lead for git help

### Not Sure About Architecture?
1. Read PHASE_5B_IMPLEMENTATION_GUIDE.md section for your subsystem
2. Look at similar classes in the codebase
3. Ask architect for design guidance

---

## Communication

**For git issues**: Ask devops-lead
**For design questions**: Ask architect
**For test coverage**: Ask qa-lead
**For vault/persistence**: Ask vault-specialist
**For anything else**: Ask team-lead

Use the /send-message command in Claude Code to reach teammates.

---

## Success Criteria

You know you're done when:

- [✓] Your subsystem is implemented
- [✓] All tests pass (including yours)
- [✓] Code is formatted (ruff clean)
- [✓] Imports work (no circular dependencies)
- [✓] Your commit is pushed to origin/feature/token-efficiency-5b
- [✓] Your documentation is complete

---

## After Everyone Is Done

When all 7 subsystems are complete:

1. Team-lead creates PR to develop
2. Architecture team reviews all commits
3. Final tests run on develop branch
4. PR is merged to develop
5. develop → main PR is created
6. Final review and merge to main

---

## Reference Documents

- **GIT_STATE_SNAPSHOT.txt** - Current branch status
- **GIT_WORKFLOW_PHASE_5B.md** - Detailed git operations
- **PHASE_5B_COMMIT_CHECKLIST.md** - Your execution guide (THE MAIN ONE)
- **PHASE_5B_IMPLEMENTATION_GUIDE.md** - Code patterns and examples
- **PHASE_5B_BRANCH_SETUP.md** - CI/CD pipeline info
- **MEMORY.md** - Project-wide patterns

---

## TL;DR

1. **Find your subsystem** in the list above
2. **Open PHASE_5B_COMMIT_CHECKLIST.md**
3. **Go to your subsystem section**
4. **Follow the checklist**
5. **Use the provided commit command**
6. **Push to feature/token-efficiency-5b**
7. **Wait for code review**
8. **Celebrate when merged!** 🎉

---

## Good Luck!

You've got everything you need. All the documentation is here. All the code is ready. All the tests are passing.

Go build something amazing! 🚀

---

**Questions?** Ask team-lead.
**Something broken?** Ask devops-lead or architect.
**Need help with code?** Look at PHASE_5B_IMPLEMENTATION_GUIDE.md.
**Confused about git?** Read GIT_WORKFLOW_PHASE_5B.md.

**Phase 5B Status**: Ready for Team Execution ✓
**Branch**: feature/token-efficiency-5b ✓
**Tests**: 892 passing ✓

Now go crush it! 💪
