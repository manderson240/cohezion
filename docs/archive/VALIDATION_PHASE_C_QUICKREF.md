# Phase C Validation - Quick Reference

## One-Command Execution

### Without BFG Output (Pre-Cleanup)
```bash
./validation_test_suite_phase_c.sh
```

### With BFG Output (Post-Cleanup)
```bash
./validation_test_suite_phase_c.sh --bfg-output bfg_output.txt
```

### Skip GitHub Tests (Offline Mode)
```bash
./validation_test_suite_phase_c.sh --bfg-output bfg_output.txt --no-github
```

## What Gets Tested

### Automated Tests (20+)

| Phase | Tests | Purpose |
|-------|-------|---------|
| **Phase 0** | 4 | Baseline: size, commits, CLAUDE.md |
| **Phase 1** | 5 | BFG output analysis (if provided) |
| **Phase 2** | 6 | Post-cleanup: integrity, size, commits |
| **Phase 3** | 6 | GitHub: remote, branch, push readiness |
| **Phase 4** | 6 | Entire.io: settings, hooks, checkpoints |

**Total**: 27+ automated tests (zero user input required)

### Manual Checks (5 Items)

| # | Checklist | When | Owner |
|----|-----------|------|-------|
| 1 | GitHub Web Verification | After push | You |
| 2 | Entire.io Cloud Sync | Post-push | You |
| 3 | Checkpoint Verification | Post-push | You |
| 4 | Size Reduction Verify | Post-cleanup | You |
| 5 | GitHub Actions/CI | Post-push | You |

## Success Criteria

- ✓ **20+ automated tests pass**
- ✓ **0 critical failures**
- ✓ **Size reduction ≥70%** (13GB → 2.5GB)
- ✓ **CLAUDE.md readable and intact**
- ✓ **All commits preserved**
- ✓ **Backup branch accessible**

## Output Files

All results saved to: `/tmp/phase_c_validation_[TIMESTAMP]/`

| File | Content |
|------|---------|
| `validation.log` | Full timestamped test output |
| `VALIDATION_PHASE_C_RESULTS.md` | Human-readable results summary |
| `bfg_output.txt` | Copy of BFG cleanup output (if provided) |
| `size_before.txt` | Git size before cleanup |
| `size_after.txt` | Git size after cleanup |

## Interpreting Results

### ✓ PASS
```
✓ VALIDATION PASSED
Status: Ready for GitHub push in Phase C
```
**Action**: Proceed with manual checks and GitHub push

### ⚠ WARN
```
⚠ VALIDATION WARNING
Status: Some warnings - review before pushing
```
**Action**: Review warnings, address if needed, can proceed cautiously

### ✗ FAIL
```
✗ VALIDATION FAILED
Status: Critical issues detected - see failures above
```
**Action**: Consult FAILURE_RECOVERY_GUIDE.md, fix issues, re-run

## Phase C Execution Timeline

```
Validation Suite:         5-10 minutes
BFG Cleanup (if run):     5-10 minutes
Git GC:                   5-10 minutes
GitHub Push:              1-5 minutes
Manual Verification:      5-10 minutes
─────────────────────────────────────
TOTAL:                    20-45 minutes
```

## Common Issues

### Issue: Size Reduction <70%
**Cause**: BFG didn't clean all files properly
**Fix**: Review BFG output, check for errors, re-run cleanup
**Guide**: FAILURE_RECOVERY_GUIDE.md section 2.1

### Issue: Push Fails
**Cause**: Auth, network, or branch issue
**Fix**: Verify GitHub auth, check network, review error
**Guide**: FAILURE_RECOVERY_GUIDE.md section 3.1

### Issue: Entire.io Not Syncing
**Cause**: Hook not installed or settings wrong
**Fix**: Check .entire/settings.json, verify hooks
**Guide**: FAILURE_RECOVERY_GUIDE.md section 4.1

## Recovery Procedures

### If Validation Fails - STOP and Recover

1. **Backup exists**: `backup/session-55-test-fixes-main` ✓
2. **View backup**: `git log backup/session-55-test-fixes-main --oneline -5`
3. **Restore if needed**: `git reset --hard backup/session-55-test-fixes-main`
4. **Review guide**: FAILURE_RECOVERY_GUIDE.md

### If Push Fails - Safe to Retry

1. **Push is idempotent** - can retry safely
2. **Check what's wrong**: Review push error output
3. **Fix locally**: Don't force-push
4. **Re-run validation**: `./validation_test_suite_phase_c.sh`
5. **Retry push**: `git push origin session-55-test-fixes-main`

## Key Files

- **This script**: `validation_test_suite_phase_c.sh` (executable)
- **Results template**: `VALIDATION_PHASE_C_RESULTS.md` (auto-filled by script)
- **Recovery guide**: `FAILURE_RECOVERY_GUIDE.md` (if issues)
- **Session overview**: `SESSION_55_OVERVIEW.md` (context)

## Before Running

```bash
# 1. Ensure you're on correct branch
git rev-parse --abbrev-ref HEAD
# Output should be: session-55-test-fixes-main

# 2. Check for uncommitted changes
git status
# Output should be: "nothing to commit, working tree clean"

# 3. Verify backup branch exists
git rev-parse backup/session-55-test-fixes-main
# Output should be: [commit SHA]

# 4. Go to repo root
cd ~/dev/cohezion
```

## During Execution

- **Watch for**: Color-coded output (green=pass, red=fail, yellow=warn)
- **Log location**: Displayed at end of script
- **Results location**: Displayed at end of script
- **Takes ~5-10 minutes**: Don't interrupt

## After Execution

1. **Review results** in output and `VALIDATION_PHASE_C_RESULTS.md`
2. **Check status**: PASS / WARN / FAIL
3. **If PASS**:
   - Review manual checklist
   - Execute Phase C (BFG cleanup, git gc, push)
4. **If WARN**:
   - Review warnings
   - Decide if safe to proceed
5. **If FAIL**:
   - Stop, don't push
   - Consult FAILURE_RECOVERY_GUIDE.md
   - Fix and re-run

## Links

- **Entire.io Docs**: https://entire.io/docs
- **GitHub Push Help**: https://docs.github.com/en/get-started/using-git/pushing-commits-to-a-remote-repository
- **Git Recovery**: https://git-scm.com/book/en/v2/Git-Internals-Maintenance-and-Data-Recovery
- **BFG Cleaner**: https://rtyley.github.io/bfg-repo-cleaner/

## Questions?

- **Validation Issues**: See FAILURE_RECOVERY_GUIDE.md
- **Phase C Steps**: See SESSION_55_OVERVIEW.md
- **Task Details**: See Task #9 definition
- **Contact**: QA Lead (Session 55)

---

**Ready?** Run: `./validation_test_suite_phase_c.sh`

**After cleanup?** Run: `./validation_test_suite_phase_c.sh --bfg-output bfg_output.txt`
