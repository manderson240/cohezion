# Rollback Quick Reference — 1-Page Emergency Card

**Print this. Keep it handy during cleanup/push.**

---

## SCENARIO LOOKUP TABLE

| If This Happens | Do This | Time | Call |
|---|---|---|---|
| `git fsck` fails, bad objects | Step 1-5 in Scenario 1 | 5 min | DevOps + Arch |
| Entire.io won't parse | Step 1-5 in Scenario 2 | 10 min | Architect |
| `git log` fails, branches broken | Step 1-5 in Scenario 3 | 15 min | DevOps + Backup |
| Merge fails, "diverged" message | Step 1-5 in Scenario 4 | 10-20 min | Team Lead |
| Tests fail in CI, unclear why | Step 1-5 in Scenario 5 | 20 min | QA + Arch |
| Entire.io says "no checkpoints" | Step 1-5 in Scenario 6 | 10 min | Arch + DevOps |

---

## EMERGENCY COMMANDS

### STOP EVERYTHING
```bash
pkill -f "git|bfg|gc" || true
rm /home/mike-anderson/dev/cohezion/.git/index.lock 2>/dev/null || true
```

### ROLLBACK TO SAFE STATE
```bash
cd /home/mike-anderson/dev/cohezion
git reset --hard backup-session-55-pre-cleanup
git push -f origin HEAD:session-55-test-fixes-main
```

### VERIFY HEALTH
```bash
git fsck --full --strict
git log --oneline -1
git status
```

---

## DECISION TREE

```
FAILURE DETECTED
    │
    ├─ Can't run git? (Scenario 1 or 3)
    │  └─ YES → ROLLBACK immediately (≤15 min)
    │
    ├─ Tests failing? (Scenario 5)
    │  └─ Investigate 15 min
    │     ├─ Root cause found? FIX and re-push
    │     └─ Still unclear? ROLLBACK
    │
    ├─ Integration failing? (Scenario 2 or 6)
    │  └─ Investigate 10 min
    │     ├─ Fix available? APPLY fix
    │     └─ Fix not clear? ROLLBACK
    │
    └─ Team branches broken? (Scenario 4)
       └─ Run recovery script for all branches
```

---

## KEY BACKUP POINTS

- **Tag**: `backup-session-55-pre-cleanup` (pre-cleanup snapshot)
- **Remotes**:
  - `origin` = GitLab (primary, localhost:8929)
  - `github` = GitHub (secondary, github.com)
- **File**: `.entire/settings.json` (Entire.io config)
- **Data**: `data/journeys/` (checkpoint storage)

---

## TIMEOUT RULES

| Task | Max Time | Then |
|------|----------|------|
| Diagnose failure | 5 min | Escalate if unclear |
| Fix attempt #1 | 10 min | Try different approach or rollback |
| Full recovery procedure | 20 min | Call for help |

---

## PHONE TREE (In Order)

1. **Team Lead** — Notify immediately of delay
2. **DevOps Lead** — If Git operations failing
3. **Architect** — If integration/design issue
4. **QA Lead** — If test failures
5. **Backup Admin** — Only if backup restore needed

---

## SUCCESS CRITERIA (After Any Recovery)

✓ `git fsck --full` passes (exit 0)
✓ `git log --oneline -1` shows valid commit
✓ `git status` is clean
✓ All remotes reachable: `git remote -v`
✓ No `.git/index.lock` file
✓ Team can pull/push normally

---

**Last Updated**: 2026-02-11
**Status**: READY FOR DEPLOYMENT
**Keep This With You During Cleanup!**
