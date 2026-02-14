# Validation Quick Start Guide
## Session 55 GitHub Push - 30-Second Reference

**Status**: Ready to execute
**Duration**: 5-10 minutes automated, 15-30 minutes manual review
**Success Rate Target**: ≥28/31 checks passing

---

## BEFORE YOU START

✓ Backup branch exists: `git branch backup/session-55-test-fixes-main`
✓ All 7 commits present: `git log --oneline -7`
✓ CLAUDE.md is readable: `wc -l CLAUDE.md` (should show ~2000)
✓ No uncommitted changes: `git status` (should be clean except untracked)

---

## EXECUTE VALIDATION

### Step 1: Run Automated Tests (5 min)
```bash
cd /home/mike-anderson/dev/cohezion
./validation_test_suite.sh
```

**Expected Output**:
- Green ✓ marks for passed tests
- Red ✗ marks for failed tests
- Yellow ⚠ marks for warnings
- Summary at end: PASS/WARN/FAIL

### Step 2: Review Results (2 min)
```bash
cat /tmp/validation_results.txt
```

**Success**: ≥20 tests passing
**Warning**: 15-19 tests passing (investigate)
**Failure**: <15 tests passing (STOP, recover)

### Step 3: Interpret Results
```
PASS ✅  → Proceed to GitHub push
WARN ⚠️  → Review warnings, proceed if acceptable
FAIL ❌  → Use FAILURE_RECOVERY_GUIDE.md
```

---

## IF VALIDATION PASSES ✅

You are cleared for GitHub push:

```bash
# Double-check remote
git remote -v

# Push to GitHub
git push origin session-55-test-fixes-main -v

# Watch for errors
# Expected: "To github.com:..."
# Expected: "[new branch] session-55-test-fixes-main -> session-55-test-fixes-main"

# Verify push succeeded
git log origin/session-55-test-fixes-main --oneline -3
```

---

## IF VALIDATION FAILS ❌

Stop. Do not push.

### Step 1: Identify Failure
Look at test name that failed, e.g.:
- `FAIL: 1.1 Repository integrity check`
- `FAIL: 3.1 Push would succeed`
- `FAIL: 4.2 Checkpoint metadata present`

### Step 2: Map to Scenario
Extract scenario ID from test name:
- 1.x → Phase 1 → Scenario C1-C5
- 2.x → Phase 2 → Scenario C1-C6
- 3.x → Phase 3 → Scenario G1-G5
- 4.x → Phase 4 → Scenario E1-E6

### Step 3: Find Recovery
Open: `FAILURE_RECOVERY_GUIDE.md`

Find section with scenario ID (e.g., "## SCENARIO C1: Repository Corruption")

Follow the decision tree and execute recommended option.

### Step 4: Retry Validation
```bash
# For Phase 1 or 2 failures:
./validation_test_suite.sh | head -50

# For Phase 3 or 4 failures:
./validation_test_suite.sh | tail -50
```

**Stop at first success.**

---

## MANUAL VERIFICATION (Post-Automation)

After automated tests pass, manually verify 5 critical items:

### 1. GitHub Web Access
```
Visit: https://github.com/[owner]/[repo]/tree/session-55-test-fixes-main
Look for:
  ✓ CLAUDE.md visible and properly formatted
  ✓ All 7 commits in history
  ✓ No encoding errors
```

### 2. Entire.io Local Status
```bash
git log entire/checkpoints/v1 --oneline -3
# Should show recent checkpoints
```

### 3. Repository Size
```bash
du -sh .git/
# Should be <6.5GB (or at least <original size)
```

### 4. Commit Integrity
```bash
git rev-parse HEAD
# Write down SHA for audit trail
```

### 5. CLAUDE.md Content
```bash
tail -20 CLAUDE.md | grep -i "complete\|ready"
# Should see completion markers
```

---

## QUICK REFERENCE: Test IDs

| ID | Phase | Category | Recovery Guide |
|----|-------|----------|-----------------|
| 1.1-1.5 | Pre-Cleanup | Repo Integrity | C1-C5 |
| 2.1-2.6 | Post-Cleanup | Data Validation | C1-C6 |
| 3.1-3.5 | GitHub Push | Remote Sync | G1-G5 |
| 4.1-4.6 | Entire.io | Integration | E1-E6 |

---

## CRITICAL CONTACTS

| Issue | Contact | Time | Authority |
|-------|---------|------|-----------|
| Repo corruption | team-lead | IMMEDIATE | Go/no-go |
| Push fails | devops-lead | URGENT (1h) | Escalation |
| Entire.io issue | qa-lead | WITHIN 2h | Advisory |
| Questions | architect | ANYTIME | Planning |

---

## SUCCESS INDICATORS ✅

You can safely proceed to GitHub push when you see:

```
✓ PASS: 1.1 Repository integrity check
✓ PASS: 1.3 All commits present (7 commits)
✓ PASS: 2.2 No git corruption after cleanup
✓ PASS: 2.3 All commits still present
✓ PASS: 2.5 CLAUDE.md intact and readable
✓ PASS: 3.1 Push would succeed (dry-run check)
✓ PASS: 4.1 Entire.io configuration correct
✓ PASS: 4.2 Checkpoint metadata present

At least 20/25 checks PASS or WARN
No critical FAIL (C1, G1 severity)
```

---

## FAILURE DECISION TREE

```
Validation Complete?
├─ YES (≥20 PASS)
│  └─ Proceed to GitHub Push ✅
├─ PARTIAL (15-19 PASS, some WARN)
│  ├─ Review warnings
│  ├─ If acceptable → Proceed ⚠️
│  └─ If not → Follow recovery
└─ NO (<15 PASS)
   ├─ Identify scenario (C1-E6)
   ├─ Open FAILURE_RECOVERY_GUIDE.md
   ├─ Follow decision tree
   ├─ Execute recovery
   └─ Re-run validation
```

---

## POST-PUSH MONITORING (After GitHub Push)

Watch for these signals for 5 minutes:

```bash
# 1. Monitor Entire.io hooks
git log entire/checkpoints/v1 --oneline -3
# Should show new checkpoint after push

# 2. Check GitHub webhook
# (GitHub notifications or status checks)

# 3. Monitor local logs
tail -50 .entire/logs/*.log 2>/dev/null
# Should show successful checkpoint capture

# 4. Verify GitLab sync (if applicable)
# Push to GitLab as secondary backup
git push gitlab session-55-test-fixes-main
```

---

## TIME BUDGETS

| Phase | Min | Max | Critical |
|-------|-----|-----|----------|
| Phase 1 | 1m | 3m | No |
| Phase 2 | 1m | 5m | No |
| Phase 3 | 2m | 5m | **YES** |
| Phase 4 | 1m | 3m | No |
| Manual | 5m | 15m | No |
| **TOTAL** | **10m** | **31m** | - |

**Red Line**: If Phase 3 (GitHub Push) fails, escalate immediately.

---

## RECOVERY TIME BUDGETS

| Scenario | Time | Can Proceed? |
|----------|------|-------------|
| C1 (corruption) | 30+ min | NO - escalate |
| C2 (commits missing) | 20+ min | NO - restore |
| C3 (backup missing) | 15+ min | NO - create |
| C4-C6 (file issues) | 5-10 min | YES - after fix |
| G1-G2 (push issues) | 10+ min | NO - fix auth/wait |
| G3-G5 (sync issues) | 10+ min | YES - after retry |
| E1-E6 (Entire.io) | 2-10 min | YES - after config |

---

## ONE-PAGE EXECUTION CHECKLIST

```
□ Pre-validation: backup branch exists
□ Pre-validation: 7 commits present
□ Pre-validation: CLAUDE.md readable
□ Pre-validation: no uncommitted changes

□ Run: ./validation_test_suite.sh
□ Review: /tmp/validation_results.txt

□ Result: ✅ PASS (≥20 tests)?
  └─ YES: Proceed to GitHub push
  └─ NO: Consult FAILURE_RECOVERY_GUIDE.md

□ GitHub push: git push origin session-55-test-fixes-main
□ Verify push succeeded (no errors)
□ Verify branch exists on GitHub
□ Verify CLAUDE.md readable on GitHub

□ Post-push: git log entire/checkpoints/v1 (verify Entire.io captured)
□ Monitoring: Watch for webhook notifications

□ All ✓: Document in session notes, mark phase complete
```

---

## STILL HAVING ISSUES?

1. **Check log file**: `/tmp/e2e_validation_*.log` (most recent)
2. **Find scenario**: Match error to Scenario ID (C1-E6)
3. **Read recovery**: FAILURE_RECOVERY_GUIDE.md → [SCENARIO]
4. **Execute fix**: Follow decision tree
5. **Contact team**: If unresolved after 15 minutes

**Do not push without passing validation.**

---

**Created**: 2026-02-11
**QA Lead**: Session 55 Validation Team
**Ready to execute**: ✅ YES
