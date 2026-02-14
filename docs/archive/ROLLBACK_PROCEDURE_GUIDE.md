# Rollback Procedure Guide — Session 55 Cleanup & Push

**Document Version**: 1.0
**Last Updated**: 2026-02-11
**Status**: READY FOR EXECUTION
**Audience**: Team lead, DevOps specialists, emergency contacts

---

## QUICK REFERENCE TABLE

| Scenario | Symptom | Recovery Time | Severity | Escalation |
|----------|---------|----------------|----------|------------|
| 1. BFG corrupts repository | `git fsck` fails, dangling objects | 5 min | CRITICAL | DevOps + Architect |
| 2. GitHub format incompatible | Entire.io can't parse journey data | 10 min | HIGH | Architect |
| 3. Repository corrupted | `git log` fails, branches broken | 15 min | CRITICAL | DevOps + Backup admin |
| 4. Team branches break | Feature branches won't merge to main | 10-20 min | HIGH | Team lead + DevOps |
| 5. E2E validation fails | Tests report failure, cause unclear | 20 min | MEDIUM | QA lead + Architect |
| 6. Entire.io can't read GitHub | Connection error or no checkpoints | 10 min | HIGH | Architect + ops |

**Emergency Hotline**: Call for help if recovery takes >5 minutes longer than estimate.

---

## SCENARIO 1: BFG Cleanup Corrupts Repository

### Symptoms
- `git fsck` reports errors beyond expected garbage collection
- Dangling objects exceed normal cleanup baseline (>1000 objects)
- Commands fail: `git log`, `git checkout`, `git branch -a`
- Error message: `fatal: bad object` or `corrupted object`

### Root Cause Analysis
**Most likely**: BFG encountered file locks or crashed mid-rewrite
**Why it happens**: Large repo rewrite + concurrent operations + incomplete BFG run

### Recovery Steps

**Step 1: Verify corruption scope** (2 min)
```bash
cd /home/mike-anderson/dev/cohezion
git fsck --full > /tmp/fsck_report.txt 2>&1
echo "=== Corruption Summary ===" && grep -c "error:" /tmp/fsck_report.txt || echo "0"
echo "=== Dangling objects ===" && grep "dangling" /tmp/fsck_report.txt | wc -l
```

**Step 2: Stop all operations** (immediate)
```bash
# Kill any running git processes
pkill -f "git|bfg" || true
# Prevent new operations
touch /home/mike-anderson/dev/cohezion/.repo-locked
```

**Step 3: Create recovery branch from GitLab backup** (1 min)
```bash
cd /tmp
git clone --mirror http://localhost:8929/root/cohezion.git cohezion-backup.git
cd cohezion-backup.git
git verify-pack -v .git/objects/pack/*.idx 2>&1 | head -20
```

**Step 4: Restore to pre-cleanup state** (2 min)
```bash
cd /home/mike-anderson/dev/cohezion
git reset --hard backup-session-55-pre-cleanup
git clean -fd
git gc --aggressive
```

**Step 5: Verify integrity** (1 min)
```bash
git fsck --full
echo "Exit code: $?"
git log --oneline -1
git status
```

### Verification Checklist
- [ ] `git fsck --full` reports clean (exit code 0)
- [ ] `git log --oneline` shows 5+ commits
- [ ] `git branch -a` lists 10+ branches
- [ ] No error messages on standard operations
- [ ] Repository size is stable: `du -sh .git`

### When to Escalate
- If Step 4 fails with "object not found"
- If fsck still reports errors after reset
- If `.git/objects` directory is corrupted beyond repair

**Call**: DevOps Lead + Architect
**Message**: "BFG recovery failed at Step X with error Y. Need full backup restore."

---

## SCENARIO 2: GitHub Push Succeeds but Format Incompatible

### Symptoms
- GitHub web UI shows commits and branches OK
- Entire.io integration fails: `Error: Cannot parse journey checkpoints`
- `.entire/settings.json` looks correct locally
- Journey data pushed but unreadable by Entire.io

### Root Cause Analysis
**Most likely**: Journey JSON schema changed or metadata encoding mismatch
**Why it happens**: BFG rewrite altered Git object properties → Entire.io parser breaks

### Recovery Steps

**Step 1: Diagnose Entire.io rejection** (3 min)
```bash
# Check if Entire.io logs are accessible
curl -s http://localhost:8929/root/cohezion/-/settings/integrations | grep -i "entire" || echo "No logs available"

# Check local .entire/settings.json
cat .entire/settings.json | jq . || echo "Invalid JSON"

# Verify checkpoint structure
find data/journeys -name "*.json" | head -3 | xargs -I {} sh -c 'echo "=== {} ===" && jq .metadata {} || echo "PARSE ERROR"'
```

**Step 2: Create rollback commit** (2 min)
```bash
cd /home/mike-anderson/dev/cohezion
git log --oneline origin/main..HEAD | head -10 > /tmp/rollback-commits.txt
echo "Commits to rollback: $(wc -l < /tmp/rollback-commits.txt)"
```

**Step 3: Force-push clean backup branch** (3 min)
```bash
git fetch origin
git reset --hard origin/main
git push --force github session-55-test-fixes-main:session-55-test-fixes-main
echo "Forced push to GitHub completed. Verify in web UI."
```

**Step 4: Wait for Entire.io to detect** (5 min, non-blocking)
```bash
# Entire.io webhook will trigger automatically
# Check status in logs after 5 minutes
sleep 300
curl -s http://localhost:8929/root/cohezion/integrations/entire.io/status || echo "Webhook pending"
```

**Step 5: Re-push once Entire.io confirms** (2 min)
```bash
# Wait for Entire.io acknowledgment
# Then proceed with corrected journey format
git push github session-55-test-fixes-main
```

### Verification Checklist
- [ ] GitHub shows commits in correct order
- [ ] Entire.io logs show successful parse (if accessible)
- [ ] `.entire/settings.json` is valid JSON
- [ ] Journey checkpoint files are readable
- [ ] Webhook completed without errors

### When to Escalate
- If Entire.io still can't parse after rollback
- If `.entire/settings.json` has structural issues
- If journey data is corrupted (can't jq parse)

**Call**: Architect
**Message**: "GitHub format incompatible with Entire.io. Need schema review for journey data."

---

## SCENARIO 3: Repository Corrupted After Cleanup

### Symptoms
- `git log` fails: `fatal: bad object`
- `git checkout` fails: `error: reference broken`
- `.git/objects` contains incomplete or truncated files
- `git gc` fails or hangs

### Root Cause Analysis
**Most likely**: Disk space exhaustion mid-cleanup OR process killed during rewrite
**Why it happens**: 2TB pack file rewrite + aggressive GC + system resource limits

### Recovery Steps

**Step 1: Stop all operations immediately** (immediate)
```bash
pkill -f "git|bfg|gc" || true
rm /home/mike-anderson/dev/cohezion/.git/index.lock 2>/dev/null || true
```

**Step 2: Check disk space** (1 min)
```bash
df -h /home/mike-anderson/dev/cohezion/.git/objects
du -sh /home/mike-anderson/dev/cohezion/.git
# Required: ≥500GB free for recovery operations
```

**Step 3: Full restore from backup branch** (5 min)
```bash
cd /home/mike-anderson/dev/cohezion
# Backup current state
tar czf /tmp/corrupted-cohezion-$(date +%s).tar.gz .git/ 2>/dev/null || true

# Reset to backup tag
git reset --hard backup-session-55-pre-cleanup
git clean -fd
git reflog expire --all --expire=now
git gc --aggressive --prune=now
```

**Step 4: Verify integrity** (2 min)
```bash
git fsck --full --strict
echo "FSK exit code: $?"
git verify-pack -v .git/objects/pack/*.idx 2>&1 | tail -5
git log --oneline -1
git rev-parse HEAD
```

**Step 5: Force-push to all remotes** (3 min)
```bash
git push -f origin HEAD:session-55-test-fixes-main
git push -f github HEAD:session-55-test-fixes-main
echo "Force-pushed to all remotes"
```

### Verification Checklist
- [ ] `git fsck --full --strict` passes (exit code 0)
- [ ] `git log --oneline` shows 10+ commits
- [ ] `git checkout main` succeeds without errors
- [ ] No `.git/index.lock` files present
- [ ] All remotes updated: `git remote -v`

### When to Escalate
- If fsck reports errors even after restore
- If `.git/objects` directory is unreadable (permissions)
- If GitLab backup tag is missing or corrupted

**Call**: DevOps Lead + Backup Admin
**Message**: "Repository corrupt beyond local repair. Need full backup restore from GitLab."

---

## SCENARIO 4: Team Branches Break After History Rewrite

### Symptoms
- `git merge main` fails with: `fatal: merge base not found`
- `git rebase main` fails: `No commits selected for rebasing`
- Feature branches show: `Your branch and main have diverged`
- Cannot push to GitHub without force flag

### Root Cause Analysis
**Most likely**: History rewrite (BFG) changed commit SHAs → team branches reference old objects
**Why it happens**: BFG rewrites history → old commits disappear → team branches orphaned

### Recovery Steps

**Step 1: Notify all team members** (1 min)
```bash
# Send to all developers on feature branches:
echo "⚠️ ALERT: Repository history rewritten. Do NOT pull main until told."
echo "Your feature branches will need rebasing. Instructions coming."
```

**Step 2: Create automated rebase script** (3 min)
```bash
cat > /tmp/team-branch-recovery.sh << 'EOF'
#!/bin/bash
set -e

BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
REMOTE="${1:-origin}"

echo "📌 Recovering branch: $BRANCH_NAME on remote: $REMOTE"

# Step 1: Fetch latest main
git fetch $REMOTE main
git fetch $REMOTE session-55-test-fixes-main

# Step 2: Create temporary backup
git branch "backup-$BRANCH_NAME-$(date +%s)" 2>/dev/null || true

# Step 3: Reset to new main base
git rebase --onto $REMOTE/main $REMOTE/session-55-test-fixes-main $BRANCH_NAME || {
  echo "❌ Rebase failed. Restoring backup."
  git rebase --abort
  exit 1
}

# Step 4: Verify no conflicts
if ! git diff --quiet --exit-code; then
  echo "⚠️ Conflicts detected. Resolve manually or restore backup."
  exit 1
fi

echo "✅ Branch $BRANCH_NAME rebased successfully."
echo "Next: git push -f $REMOTE $BRANCH_NAME"
EOF

chmod +x /tmp/team-branch-recovery.sh
echo "Rebase script created: /tmp/team-branch-recovery.sh"
```

**Step 3: Provide recovery instructions to each developer** (2 min)
```bash
cat > /tmp/DEVELOPER_RECOVERY_STEPS.md << 'EOF'
# Your Branch Recovery Instructions

## What Happened
Repository history was rewritten. Your feature branch now points to deleted commits.

## Recovery (3 steps)

### 1. DO NOT PULL MAIN YET
```bash
git fetch origin
# DON'T do: git pull origin main  ← This will break everything
```

### 2. Run Recovery Script
```bash
bash /tmp/team-branch-recovery.sh origin
# If this fails, restore your backup: git checkout backup-YOUR-BRANCH-NAME
```

### 3. Force-Push Your Branch
```bash
git push -f origin YOUR-BRANCH-NAME
```

## If Something Goes Wrong
Restore your backup:
```bash
git reset --hard backup-YOUR-BRANCH-NAME
git push -f origin YOUR-BRANCH-NAME
```

Contact: Team Lead
EOF

echo "Developer instructions created: /tmp/DEVELOPER_RECOVERY_STEPS.md"
```

**Step 4: Run recovery for each team branch** (2 min per branch)
```bash
# For each active feature branch:
for branch in $(git branch -r --list "origin/feature/*" "origin/session-*"); do
  BRANCH_NAME=$(basename $branch)
  echo "Recovering $BRANCH_NAME..."
  bash /tmp/team-branch-recovery.sh origin || echo "FAILED: $BRANCH_NAME needs manual recovery"
done
```

**Step 5: Verify all branches can merge** (2 min)
```bash
for branch in $(git branch -r); do
  BRANCH_NAME=$(basename $branch)
  git merge-base --is-ancestor $branch HEAD && echo "✅ $BRANCH_NAME" || echo "❌ $BRANCH_NAME - NEEDS RECOVERY"
done
```

### Verification Checklist
- [ ] All feature branches rebased on new main
- [ ] No "diverged" messages on `git status`
- [ ] All branches can merge without conflicts
- [ ] Force-push succeeds for all branches
- [ ] Team members confirm their branches work

### When to Escalate
- If rebase script fails for >2 branches
- If conflicts too complex to auto-resolve
- If backup branches are corrupted

**Call**: Team Lead + DevOps
**Message**: "Need assistance recovering N team branches after history rewrite."

---

## SCENARIO 5: E2E Validation Fails Post-Push

### Symptoms
- CI/CD pipeline shows red X
- Test output: `FAILED tests/test_X.py::test_Y`
- Error message is cryptic or incomplete
- Not clear if it's a test bug or real code regression

### Root Cause Analysis
**Most likely causes** (in order):
1. Test isolation issue (singleton not reset)
2. Import path changed after history rewrite
3. Actual code regression (should not happen)
4. Missing dependency after cleanup

### Investigation Decision Matrix

```
┌─ Is test failure reproducible locally?
│
├─ YES → Is test only failing in CI?
│        ├─ YES → Likely environmental issue (Python version, dependency version)
│        │        ACTION: Update CI config, re-run
│        └─ NO  → Actual regression
│                 ACTION: Fix code, re-test locally, re-push
│
└─ NO  → Is failure intermittent?
         ├─ YES → Test isolation bug
         │        ACTION: Add singleton reset, re-run
         └─ NO  → Flaky test or environmental
                  ACTION: Check CI logs, isolate test, disable if urgent
```

### Recovery Steps

**Step 1: Get full test output** (2 min)
```bash
# Download CI logs
# Option A: GitHub Actions UI → run logs
# Option B: If local:
cd /home/mike-anderson/dev/cohezion
uv run pytest tests/test_failing.py::test_name -vv > /tmp/test_output.txt 2>&1
cat /tmp/test_output.txt
```

**Step 2: Classify failure type** (3 min)
```bash
# Check if test passes locally
uv run pytest tests/test_failing.py::test_name -x

if [ $? -eq 0 ]; then
  echo "✅ CLASSIFICATION: Environmental issue (passes locally, fails in CI)"
  FAILURE_TYPE="environmental"
else
  echo "❌ CLASSIFICATION: Reproducible regression"
  FAILURE_TYPE="regression"
fi
```

**Step 3: Branch-specific recovery**

**IF: Environmental Issue** (5 min total)
```bash
# Update CI config with correct Python/dependency versions
# Option A: Check GitHub Actions runner
# Option B: Check dependency incompatibility
uv pip list | grep -i "pytest\|asyncio\|numpy" | head -5

# Fix: Update GitHub CI YAML or uv.lock
# Then: Push fix + re-run CI
git add -A
git commit -m "fix: Update CI environment for Python X.Y"
git push origin session-55-test-fixes-main
```

**IF: Regression** (5 min investigation + fix time)
```bash
# Identify which change caused it
git log --oneline -20 > /tmp/recent-commits.txt
git bisect start
# ... follow bisect instructions to find exact commit

# Once found:
git revert [commit-sha]
git push origin session-55-test-fixes-main
# CI will re-run with revert
```

**IF: Test Isolation** (5 min)
```bash
# Add singleton reset to conftest.py
echo "Adding singleton reset to tests/conftest.py..."
# See conftest.py line 85-88 for pattern

# Re-run test
uv run pytest tests/conftest.py::test_reset -vv
uv run pytest tests/test_failing.py::test_name -vv
```

**Step 4: Re-run full E2E suite locally** (10 min)
```bash
uv run pytest tests/ -x --tb=short 2>&1 | tee /tmp/e2e-results.txt
echo "Pass rate: $(grep -c PASSED /tmp/e2e-results.txt)/$(grep -c -E "PASSED|FAILED" /tmp/e2e-results.txt)"
```

**Step 5: If still failing, rollback push** (5 min)
```bash
# If investigation takes >15 minutes, rollback and investigate later
git reset --hard origin/main
git push -f origin session-55-test-fixes-main

# Schedule investigation for later session
echo "TODO: Debug test failure XYZ in next session" >> MEMORY.md
```

### Verification Checklist
- [ ] Understand root cause (environmental/regression/isolation)
- [ ] Test passes locally (or properly skipped)
- [ ] CI re-run shows green checkmarks
- [ ] No other tests broken by fix
- [ ] Git log shows proper commit history

### When to Escalate
- If root cause unclear after 15 minutes
- If fix causes other tests to fail
- If multiple test failures (suggests systemic issue)

**Call**: QA Lead + Architect
**Message**: "E2E validation failing on test XYZ. Root cause unclear, need help."

---

## SCENARIO 6: Entire.io Can't Read GitHub After Push

### Symptoms
- Entire.io dashboard shows: `Error: Cannot connect to repository`
- Or: `No checkpoints found` (but checkpoints exist in GitHub)
- GitHub API health check passes
- Local clone of GitHub works fine

### Root Cause Analysis
**Most likely causes** (in order):
1. `.entire/settings.json` missing or corrupted on GitHub
2. GitHub webhook token expired or misconfigured
3. Journey checkpoint metadata incompatible with Entire.io parser
4. GitHub API rate limits hit (unlikely but possible)

### Recovery Steps

**Step 1: Verify GitHub repository state** (2 min)
```bash
# Check if .entire directory pushed correctly
git ls-remote github | grep -i "entire" || echo "Checking all refs..."
git ls-remote github | head -20

# Check specific file
git show github/session-55-test-fixes-main:.entire/settings.json | jq . || echo "File missing or invalid JSON"
```

**Step 2: Verify checkpoint metadata** (2 min)
```bash
# Check journey checkpoint structure
git show github/session-55-test-fixes-main:data/journeys/current.json 2>/dev/null | jq .metadata || echo "No journeys found"

# Check if metadata has required Entire.io fields
git show github/session-55-test-fixes-main:data/journeys/current.json 2>/dev/null | jq 'keys' | grep -E "session_id|timestamp|checkpoints"
```

**Step 3: Fix .entire/settings.json if needed** (3 min)
```bash
# Check local version
cat .entire/settings.json | jq .

# If invalid, restore from template:
cat > .entire/settings.json << 'EOF'
{
  "version": "1.0",
  "entire_io": {
    "enabled": true,
    "api_endpoint": "https://api.entire.io",
    "repository_id": "cohezion-session-55"
  },
  "checkpoint": {
    "path": "data/journeys",
    "format": "json",
    "metadata_fields": ["session_id", "timestamp", "status"]
  }
}
EOF

git add .entire/settings.json
git commit -m "fix: Restore .entire/settings.json"
git push origin session-55-test-fixes-main
```

**Step 4: Manually trigger Entire.io sync** (5 min, non-blocking)
```bash
# Option A: If Entire.io API available:
curl -X POST https://api.entire.io/sync \
  -H "Authorization: Bearer $ENTIRE_IO_TOKEN" \
  -d '{"repository": "cohezion-session-55"}' 2>/dev/null || echo "API call failed"

# Option B: If using local Entire.io:
# Restart webhook handler or re-register repository

# Option C: Wait for next scheduled sync (usually 5-30 min)
echo "Waiting for Entire.io webhook to trigger..."
sleep 300
```

**Step 5: Verify Entire.io can read data** (2 min)
```bash
# Test if Entire.io dashboard loads journeys
# Check dashboard at: https://entire.io/cohezion-session-55
# Or local instance: http://localhost:7070

# CLI verification (if available):
curl -s http://localhost:7070/api/journeys | jq '.count' || echo "Endpoint not available"
```

### Verification Checklist
- [ ] `.entire/settings.json` valid JSON in GitHub
- [ ] Journey checkpoint files readable from GitHub
- [ ] Entire.io webhook shows successful sync in logs
- [ ] Dashboard loads without errors
- [ ] At least one checkpoint visible in Entire.io

### When to Escalate
- If `.entire/settings.json` is correctly formatted but still fails
- If GitHub API is returning errors
- If Entire.io webhook is not triggering

**Call**: Architect + DevOps
**Message**: "Entire.io integration failing. Settings correct but sync not triggering."

---

## MASTER DECISION MATRIX

Use this to decide: Rollback vs Continue vs Investigate?

```
FAILURE TYPE          │ SEVERITY │ AUTO-FIX? │ DECISION
──────────────────────┼──────────┼───────────┼─────────────────────
BFG corrupts repo     │ CRITICAL │ NO        │ → ROLLBACK immediately
Format incompatible   │ HIGH     │ MAYBE     │ → Investigate 5 min, then rollback or fix
Repo corrupted        │ CRITICAL │ NO        │ → ROLLBACK immediately
Team branches break   │ HIGH     │ YES       │ → RECOVER branches in parallel
E2E validation fails  │ MEDIUM   │ YES       │ → Investigate 15 min, then fix or rollback
Entire.io can't read  │ HIGH     │ MAYBE     │ → Investigate 10 min, then fix or debug
```

**CRITICAL Rule**: If recovery estimate exceeds 20 minutes, ROLLBACK and try again later.

---

## ESCALATION CONTACTS

| Role | Contact | Use When | Response Time |
|------|---------|----------|----------------|
| **Team Lead** | In-session message | Anything blocking team | Immediate |
| **DevOps Lead** | In-session message | Git/infrastructure issues | <5 min |
| **Architect** | In-session message | Design/integration issues | <10 min |
| **QA Lead** | In-session message | Test failures | <10 min |
| **Backup Admin** | In-session message | Backup restore needed | <15 min |

---

## ROLLBACK VERIFICATION CHECKLIST

After ANY recovery procedure, verify these:

- [ ] `git status` is clean
- [ ] `git log --oneline` shows 10+ commits
- [ ] `git fsck --full` passes (exit 0)
- [ ] All remotes updated: `git remote -v`
- [ ] Main branch is stable: `git checkout main && git pull`
- [ ] No `.git/index.lock` files present
- [ ] `du -sh .git` shows reasonable size (~500MB-1.5GB)
- [ ] Team notified of completion
- [ ] Post-incident review scheduled

---

## PREVENTION CHECKLIST

For next session, prevent failures:

- [ ] Back up HEAD before cleanup: `git tag backup-session-XX-pre-cleanup`
- [ ] Run `git fsck --full` before and after BFG
- [ ] Notify all team members 24h before history rewrite
- [ ] Test push to GitHub staging first (if available)
- [ ] Schedule E2E validation before production push
- [ ] Have backup admin on standby during push

---

## APPENDIX: Command Reference

**Emergency Stops**
```bash
pkill -f "git|bfg|gc"  # Kill all Git operations
touch .repo-locked     # Prevent new operations
```

**Quick Rollback**
```bash
git reset --hard backup-session-55-pre-cleanup
git push -f origin HEAD:session-55-test-fixes-main
```

**Repository Health Check**
```bash
git fsck --full --strict
git verify-pack -v .git/objects/pack/*.idx | tail -10
du -sh .git/objects .git/refs .git/logs
```

**Verify All Branches**
```bash
for branch in $(git branch -a); do
  git merge-base --is-ancestor $branch HEAD && echo "✅ $branch" || echo "❌ $branch"
done
```

---

**Document Status**: READY FOR USE
**Last Verified**: Session 55 Preparation
**Next Review**: After cleanup execution
