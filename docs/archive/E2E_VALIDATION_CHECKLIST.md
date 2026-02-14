# End-to-End Validation Checklist
## GitHub Push + Entire.io Integration Verification

**Purpose**: Verify that GitHub push succeeds AND Entire.io integration works correctly
**Scope**: Session 55, branch `session-55-test-fixes-main`
**Created**: 2026-02-11
**QA Lead**: Session 55 Validation Team

---

## CRITICAL PATH CHECKLIST

### Phase 1: Pre-Cleanup Validation (5 checks)
Verify repository integrity before any cleanup operations.

#### 1.1 Repository Integrity Check
**Test Command**:
```bash
git fsck --full --progress 2>&1 | tail -5
```
**Expected Result**:
- Output ends with: `Checking connectivity: done.`
- No lines containing: `ERROR`, `broken`, `corrupt`, `missing`
- Exit code: 0

**Failure Action**:
- If corruption detected: Stop immediately, escalate to team-lead
- If minor warnings: Document in repair log, proceed with caution
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario C1

---

#### 1.2 Git Repository Size Baseline
**Test Command**:
```bash
du -sh .git/ | tee /tmp/git_size_before.txt
```
**Expected Result**:
- Output format: `7.2G	.git/` (or similar size ~7-8GB)
- Actual size between 6-9GB (repository is large but reasonable)

**Failure Action**:
- If >10GB: Repository may have bloat, investigate with git gc
- If <5GB: Unexpected size change, verify nothing was deleted
- Record baseline for post-cleanup comparison

---

#### 1.3 Verify All 7 Commits Present
**Test Command**:
```bash
git log --oneline -10 | tee /tmp/commits_before.txt
```
**Expected Result**:
- Shows exactly 7 commits in session-55-test-fixes-main branch:
  ```
  ddc56ac9c6a5 docs: Session 55 escalation solution - use GitLab primary, GitHub secondary
  54d151734caf docs: Phase 3 execution checkpoint - pending GitHub verification
  d9c6a6cb4258 docs: Create compound engineering plan for token-efficient repo fix
  99b054b35c88 docs: Add guide for setting up GitHub and GitLab MCP servers
  8948742eea74 docs: Session 55 deployment summary - CLAUDE.md foundation ready for production
  8a96130891fa docs: Add deployment guide for CLAUDE.md foundation optimization
  69bd7cff36f2 docs: Optimize CLAUDE.md for token efficiency, compound engineering, and agent observability
  ```
- SHAs are exactly as shown (no modifications)

**Failure Action**:
- If commits missing: Investigate with `git reflog`
- If SHAs differ: Commits were rebased/modified, investigate why
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario C2

---

#### 1.4 Verify No Uncommitted Changes
**Test Command**:
```bash
git status --porcelain | tee /tmp/git_status_before.txt
```
**Expected Result**:
- Output shows only modified tracked files and untracked files
- No errors or warnings
- All changes either staged or documented

**Failure Action**:
- If unintended deletions shown: Investigate with `git diff --name-status`
- If merge conflicts shown: Resolve before proceeding
- Document all pending changes

---

#### 1.5 Verify Backup Branch Created and Accessible
**Test Command**:
```bash
git rev-parse backup/session-55-test-fixes-main && echo "Backup branch exists"
git log backup/session-55-test-fixes-main --oneline -3
```
**Expected Result**:
- First command outputs the SHA of backup branch HEAD
- Second command shows 3+ commits from backup
- Backup branch points to same commits as current branch

**Failure Action**:
- If backup doesn't exist: Create with `git branch backup/session-55-test-fixes-main`
- If backup is stale: Delete and recreate from current branch
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario C3

---

### Phase 2: Post-Cleanup Validation (6 checks)
Verify repository integrity after cleanup operations.

#### 2.1 Verify Repository Size Reduction
**Test Command**:
```bash
du -sh .git/ | tee /tmp/git_size_after.txt
BEFORE=$(grep -oE '[0-9.]+' /tmp/git_size_before.txt | head -1)
AFTER=$(grep -oE '[0-9.]+' /tmp/git_size_after.txt | head -1)
echo "Size reduction: ${BEFORE}GB → ${AFTER}GB"
```
**Expected Result**:
- Final size <6.5GB (at least 10% reduction from ~7.2GB)
- No errors during cleanup
- Exit code: 0

**Failure Action**:
- If size increased: Cleanup didn't work, investigate with `git gc --aggressive`
- If size unchanged: Run `git gc` manually and retest
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario C4

---

#### 2.2 Verify No Git Corruption After Cleanup
**Test Command**:
```bash
git fsck --full --progress 2>&1 | tail -5
```
**Expected Result**:
- Output: `Checking connectivity: done.`
- No errors or broken objects
- Exit code: 0

**Failure Action**:
- If corruption detected: Rollback with backup branch immediately
- If warnings only: Document and continue monitoring
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario C1

---

#### 2.3 Verify All 7 Commits Still Present
**Test Command**:
```bash
git log --oneline -10 | tee /tmp/commits_after.txt
diff /tmp/commits_before.txt /tmp/commits_after.txt
```
**Expected Result**:
- `diff` output is empty (commits unchanged)
- All 7 commits still visible
- Commit SHAs identical to before cleanup

**Failure Action**:
- If any commit missing: Restore from backup branch
- If SHAs changed: Commits were modified, investigate why
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario C2

---

#### 2.4 Verify Commit SHAs Unchanged
**Test Command**:
```bash
echo "Before:" && git log --format=%H -n 1 < /tmp/commits_before.txt
echo "After:" && git rev-parse HEAD
```
**Expected Result**:
- Before SHA: `ddc56ac9c6a5...` (latest commit)
- After SHA: `ddc56ac9c6a5...` (same)
- All 7 commit SHAs identical

**Failure Action**:
- If SHAs changed: Commits were modified, investigate why
- If any commit missing: Restore from backup
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario C5

---

#### 2.5 Verify CLAUDE.md Intact and Readable
**Test Command**:
```bash
head -50 CLAUDE.md && echo "---" && tail -20 CLAUDE.md
wc -l CLAUDE.md
```
**Expected Result**:
- File is readable (no encoding errors)
- First 50 lines show proper markdown structure
- Last 20 lines present (no truncation)
- Word count: ~2000 lines (±5%)

**Failure Action**:
- If file corrupted: Restore from git history with `git checkout HEAD~1 CLAUDE.md`
- If encoding issues: Verify UTF-8 with `file CLAUDE.md`
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario C6

---

#### 2.6 Verify Repository Functional
**Test Command**:
```bash
git rev-parse HEAD
git log --oneline -1
git status
git remote -v
```
**Expected Result**:
- `rev-parse`: Shows current HEAD SHA (ddc56ac9c6a5...)
- `log`: Shows latest commit message
- `status`: "On branch session-55-test-fixes-main"
- `remote`: Shows origin pointing to GitHub/GitLab

**Failure Action**:
- If any command fails: Repository is corrupted, stop
- If remote missing: Add with `git remote add origin <url>`
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario C1

---

### Phase 3: GitHub Push Validation (5 checks)
Verify that push to GitHub succeeds and all data is accessible.

#### 3.1 Verify Push Succeeds
**Test Command**:
```bash
git push origin session-55-test-fixes-main -v 2>&1 | tee /tmp/push_output.txt
echo "Exit code: $?"
```
**Expected Result**:
- Output includes: `To github.com:...`
- Output includes: `[new branch] session-55-test-fixes-main -> session-55-test-fixes-main`
- No lines containing: `ERROR`, `rejected`, `failed`
- Exit code: 0

**Failure Action**:
- If authentication fails: Verify GitHub token is valid
- If branch already exists: Use `git push --force-with-lease` (safe force push)
- If quota exceeded: Wait 5 minutes and retry
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario G1

---

#### 3.2 Verify No HTTP 500 Errors
**Test Command**:
```bash
grep -i "500\|error\|failed" /tmp/push_output.txt || echo "No 500 errors detected"
```
**Expected Result**:
- No lines containing "500", "error", or "failed"
- Exit code: 0

**Failure Action**:
- If 500 errors found: GitHub may be having issues, retry in 5 minutes
- If other errors: Check GitHub status page at https://www.githubstatus.com
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario G2

---

#### 3.3 Verify Branch Exists on GitHub
**Test Command**:
```bash
git ls-remote origin session-55-test-fixes-main | tee /tmp/remote_verify.txt
```
**Expected Result**:
- Output: `ddc56ac9c6a5...  refs/heads/session-55-test-fixes-main`
- SHA matches local HEAD
- Exit code: 0

**Failure Action**:
- If branch not found: Push may have failed silently, retry
- If SHA mismatch: Push was partial, investigate with `git fetch` and retry
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario G3

---

#### 3.4 Verify All 7 Commits on GitHub
**Test Command**:
```bash
gh api repos/{owner}/{repo}/commits?sha=session-55-test-fixes-main --jq '.[] | .sha' 2>/dev/null | wc -l
# If gh CLI not available:
git fetch origin && git log origin/session-55-test-fixes-main --oneline -7
```
**Expected Result**:
- Count: 7 commits (or all commits visible)
- All commit SHAs match local commits
- Exit code: 0

**Failure Action**:
- If fewer commits: Push was incomplete, retry
- If SHAs mismatch: Commits were modified on GitHub, investigate
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario G4

---

#### 3.5 Verify CLAUDE.md Readable on GitHub Web
**Test Command**:
```bash
curl -s https://raw.githubusercontent.com/{owner}/{repo}/session-55-test-fixes-main/CLAUDE.md | head -50
```
**Expected Result**:
- HTTP 200 status (success)
- First 50 lines of CLAUDE.md returned
- Valid markdown (no encoding errors)
- Contains "# Cohezion" header

**Failure Action**:
- If 404 error: File not found on GitHub, verify push succeeded
- If 403 error: Repository may be private, check GitHub settings
- If encoding errors: Retry with `git push --force-with-lease`
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario G5

---

### Phase 4: Entire.io Integration Validation (6 checks)
Verify that Entire.io successfully captured the push and integration works.

#### 4.1 Verify Entire.io Configuration
**Test Command**:
```bash
cat .entire/settings.json | grep -E '"strategy"|"enabled"'
ls -la .entire/ | grep -E 'settings|\.gitignore'
```
**Expected Result**:
- JSON file contains: `"strategy": "manual-commit"`
- JSON file contains: `"enabled": true`
- Files shown: `settings.json`, `.gitignore`

**Failure Action**:
- If settings missing: Create with proper configuration
- If strategy wrong: Update to `manual-commit`
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario E1

---

#### 4.2 Verify Checkpoint Metadata Present
**Test Command**:
```bash
git log entire/checkpoints/v1 --format="%B" -1 | grep -E "Entire-Session|Entire-Strategy"
git log entire/checkpoints/v1 --oneline -3
```
**Expected Result**:
- Output includes: `Entire-Session: <UUID>`
- Output includes: `Entire-Strategy: manual-commit`
- Shows 3+ checkpoints in log
- Latest checkpoint visible and recent

**Failure Action**:
- If metadata missing: Entire.io hooks may not have run
- If checkpoint missing: Check Entire.io hooks are installed in `.git/hooks/`
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario E2

---

#### 4.3 Verify Agent Context Captured
**Test Command**:
```bash
git log entire/checkpoints/v1 --format="%B" -1 | head -20
# Or if checkpoint files available:
git show entire/checkpoints/v1:*/0/context.md 2>/dev/null | head -50
```
**Expected Result**:
- Output shows: Session ID (UUID format)
- Output shows: Timestamp of capture
- Output shows: List of files modified
- Output shows: Agent identification (Claude Code)

**Failure Action**:
- If context empty: Entire.io didn't capture prompts
- If session ID missing: Metadata may be incomplete
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario E3

---

#### 4.4 Verify Journey Data Structured Correctly
**Test Command**:
```bash
git show entire/checkpoints/v1:cf/d96021b5cc/0/content_hash.txt 2>/dev/null || echo "Checkpoint found"
git log entire/checkpoints/v1 --format="%h %s" -5 | grep -i checkpoint
```
**Expected Result**:
- Shows checkpoint directory structure (cf/, 4f/, etc.)
- Output includes: "Checkpoint:" in commit messages
- Each checkpoint has: content_hash.txt and context.md files
- Format matches Entire.io specification

**Failure Action**:
- If structure wrong: Entire.io may be using different format
- If checkpoints missing: Manual-commit strategy may not be working
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario E4

---

#### 4.5 Verify CLAUDE.md Indexed by Entire.io
**Test Command**:
```bash
git show entire/checkpoints/v1:*/0/context.md 2>/dev/null | grep -i "claude\|token-efficient" | head -5
```
**Expected Result**:
- Output contains: References to CLAUDE.md
- Output contains: "token-efficient" or "compound engineering"
- Output shows: File was considered during session
- Exit code: 0 (file found)

**Failure Action**:
- If no results: CLAUDE.md may not have been in checkpoint
- If encoding error: File format may be incompatible
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario E5

---

#### 4.6 Verify Entire.io Integration Working
**Test Command**:
```bash
# If entire CLI available:
entire status 2>/dev/null || echo "Entire CLI check skipped"
# Manual verification:
git branch -r | grep entire/checkpoints
git fetch origin && git log origin/entire/checkpoints/v1 --oneline -2 2>/dev/null || echo "Remote checkpoint branch exists"
```
**Expected Result**:
- `entire status`: Shows "Last sync: <recent timestamp>"
- `git branch`: Shows `origin/entire/checkpoints/v1`
- `git log`: Shows recent checkpoint commits synced
- Exit code: 0

**Failure Action**:
- If status shows "never": Cloud sync may not be enabled (acceptable)
- If branch missing: Checkpoints are local only (acceptable)
- If no recent commits: Sync may be lagging (try `entire push`)
- Recovery: See FAILURE_RECOVERY_GUIDE.md → Scenario E6

---

## DECISION TREE FOR VALIDATION FAILURES

### Critical Path Failure Flow Chart

```
START VALIDATION
├─ PHASE 1 (Pre-Cleanup) FAILS
│  ├─ Repo Integrity (1.1): STOP → Escalate to team-lead
│  ├─ Commits Missing (1.3): STOP → Restore from backup
│  ├─ Backup Missing (1.5): STOP → Create backup, restart
│  └─ Other (1.2, 1.4): DOCUMENT → Continue with caution
│
├─ PHASE 2 (Post-Cleanup) FAILS
│  ├─ Repo Corrupted (2.2): ROLLBACK → Restore from backup
│  ├─ Commits Lost (2.3, 2.4): ROLLBACK → Restore from backup
│  ├─ CLAUDE.md Corrupted (2.5): RESTORE → git checkout HEAD~1 CLAUDE.md
│  └─ Size Check (2.1): WARN → Continue, monitor
│
├─ PHASE 3 (GitHub Push) FAILS
│  ├─ Push Fails (3.1): RETRY → Check auth, network, quota
│  ├─ HTTP 500 (3.2): WAIT → 5 min, check GitHub status, retry
│  ├─ Branch Not Found (3.3, 3.4): INVESTIGATE → git fetch, check git log
│  └─ CLAUDE.md Not Readable (3.5): RETRY → Force push, verify encoding
│
└─ PHASE 4 (Entire.io) FAILS
   ├─ Config Wrong (4.1): UPDATE → Edit settings.json, re-enable hooks
   ├─ No Checkpoint (4.2): CHECK → ls .git/hooks/, reinstall if needed
   ├─ Context Missing (4.3, 4.4): INVESTIGATE → Entire.io may not be capturing
   ├─ CLAUDE.md Not Indexed (4.5): OK → Can re-index manually
   └─ Cloud Sync Not Working (4.6): OK → Local capture still works
```

---

## REMEDIATION BY SCENARIO

### Remediation Quick Reference

| Failure | Likely Cause | Quick Fix | Full Documentation |
|---------|--------------|-----------|-------------------|
| Repo corruption (2.2) | Bad cleanup | Restore from backup | C1 |
| Commits missing (2.3) | Incomplete push | git fetch + reflog | C2 |
| Backup missing (1.5) | Not created | git branch backup/... | C3 |
| Size unchanged (2.1) | gc failed | git gc --aggressive | C4 |
| SHA mismatch (2.4) | Rebase occurred | Verify intentional | C5 |
| CLAUDE.md corrupt (2.5) | Bad write | git checkout HEAD~1 | C6 |
| Push rejected (3.1) | Auth/branch exists | Force push or re-auth | G1 |
| HTTP errors (3.2) | GitHub outage | Wait 5 min, retry | G2 |
| Branch missing (3.3) | Incomplete push | git push -u origin | G3 |
| Commits on GitHub (3.4) | Partial sync | git fetch, check log | G4 |
| File not readable (3.5) | Encoding issue | git push --force-with-lease | G5 |
| Entire config wrong (4.1) | Not configured | cat .entire/settings.json | E1 |
| No checkpoint (4.2) | Hooks not installed | entire enable, recommit | E2 |
| Context missing (4.3) | Entire not capturing | Check prompt logs | E3 |
| Wrong structure (4.4) | Format error | Manual checkpoint creation | E4 |
| CLAUDE.md not indexed (4.5) | Timing issue | Re-run entire capture | E5 |
| Sync not working (4.6) | Cloud issue | Run `entire push` manually | E6 |

---

## SUCCESS CRITERIA

✅ **VALIDATION PASSED** if:
- All Phase 1 checks pass (pre-cleanup validation)
- All Phase 2 checks pass (post-cleanup validation)
- At least 4 of 5 Phase 3 checks pass (GitHub push)
- At least 4 of 6 Phase 4 checks pass (Entire.io integration)

❌ **VALIDATION FAILED** if:
- Any Phase 1 check fails
- Any Phase 2 critical check fails (2.1, 2.2, 2.3, 2.4)
- Phase 3 push fails (3.1)
- All Phase 4 checks fail

⚠️ **VALIDATION WARNING** if:
- Phase 2 size check doesn't show reduction (monitor)
- Phase 3 optional checks fail (file readable)
- Phase 4 cloud sync checks fail (local capture still works)

---

## NEXT STEPS AFTER VALIDATION

### If PASSED:
1. Document results in `/tmp/validation_results.txt`
2. Merge to main branch: `git checkout main && git merge session-55-test-fixes-main`
3. Push to both GitHub and GitLab
4. Notify team-lead of success
5. Archive validation logs for audit trail

### If FAILED:
1. Review FAILURE_RECOVERY_GUIDE.md for appropriate scenario
2. Execute remediation steps
3. Re-run failed phase(s) only
4. Document root cause in session notes
5. Escalate to team-lead if critical failures

---

**Created**: 2026-02-11
**QA Specialist**: Session 55 Validation Team
**Review Status**: Ready for automated test script
