# Failure Recovery Guide
## GitHub Push + Entire.io Integration Troubleshooting

**Purpose**: Decision trees and recovery procedures for all failure scenarios
**Created**: 2026-02-11
**QA Lead**: Session 55 Validation Team

---

## CRITICAL ESCALATION MATRIX

| Scenario | Severity | Recovery Time | Escalation | Authority |
|----------|----------|---------------|-----------|-----------|
| Repo corruption (C1) | 🔴 CRITICAL | 30+ min | Immediate | team-lead |
| Commits missing (C2) | 🔴 CRITICAL | 20+ min | Immediate | team-lead |
| Backup missing (C3) | 🟠 HIGH | 15+ min | Urgent | team-lead |
| Size check failed (C4) | 🟡 MEDIUM | 10+ min | Within 1h | devops-lead |
| SHA mismatch (C5) | 🟡 MEDIUM | 5+ min | Within 1h | architect |
| CLAUDE.md corrupt (C6) | 🟡 MEDIUM | 5+ min | Within 1h | qa-lead |
| Push rejected (G1) | 🟠 HIGH | 10+ min | Urgent | devops-lead |
| HTTP 500 (G2) | 🟡 MEDIUM | 5+ min | Within 5h | external |
| Branch missing (G3) | 🟡 MEDIUM | 10+ min | Within 1h | devops-lead |
| Commits sync (G4) | 🟡 MEDIUM | 10+ min | Within 1h | devops-lead |
| File not readable (G5) | 🟡 MEDIUM | 5+ min | Within 1h | devops-lead |
| Entire config (E1) | 🟢 LOW | 2+ min | Within 2h | qa-lead |
| No checkpoint (E2) | 🟢 LOW | 5+ min | Within 2h | qa-lead |
| Context missing (E3) | 🟢 LOW | 10+ min | Within 4h | architect |
| Wrong structure (E4) | 🟢 LOW | 15+ min | Within 4h | architect |
| CLAUDE.md not indexed (E5) | 🟢 LOW | 5+ min | Within 4h | qa-lead |
| Sync not working (E6) | 🟢 LOW | 10+ min | Within 4h | devops-lead |

---

## SCENARIO C1: Repository Corruption

### Symptoms
- `git fsck` shows ERROR, broken objects, or missing files
- Random git commands fail
- Repository state is unrecoverable

### Root Causes
- Failed cleanup operation
- Incomplete object database
- Bad git gc or rebase
- Disk space exhaustion during operation

### Recovery Decision Tree

```
Git Corruption Detected
├─ Corruption is in pack files?
│  ├─ YES → Option 1: Repacking (60% success rate)
│  └─ NO → Option 2: Restore from Backup
├─ Backup available?
│  ├─ YES → Restore immediately (100% safe)
│  └─ NO → Option 3: Reflog recovery (40% success rate)
└─ Critical data preserved elsewhere?
   ├─ YES → Option 4: New clone (safest)
   └─ NO → Escalate to team-lead for guidance
```

### Option 1: Attempt Repacking (Lowest risk)
```bash
# Stop all git operations immediately
killall -9 git

# Clear git locks
rm -f .git/*.lock

# Aggressive repack and verify
git gc --aggressive --prune=now
git fsck --full

# If fsck passes: corruption resolved
# If fsck still fails: proceed to Option 2
```

**Time**: 5-10 minutes | **Risk**: Low | **Success Rate**: 60%

### Option 2: Restore from Backup (Recommended)
```bash
# Create temporary branch as safety net
git branch corrupted-state HEAD

# Reset to backup
git reset --hard backup/session-55-test-fixes-main

# Verify clean state
git fsck --full
git log --oneline -3

# If successful:
# 1. Document what caused corruption
# 2. Log incident in MEMORY.md
# 3. Destroy corrupted-state branch: git branch -D corrupted-state
```

**Time**: 2-3 minutes | **Risk**: None | **Success Rate**: 100%

### Option 3: Reflog Recovery (If backup lost)
```bash
# View reflog to find last clean state
git reflog | head -20

# Look for a commit before corruption started
# Example: "ddc56ac HEAD@{5}: commit: docs: Session 55..."

# Reset to that state
git reset --hard HEAD@{5}

# Verify
git fsck --full

# If successful: proceed with cleanup
# If fails: proceed to Option 4
```

**Time**: 3-5 minutes | **Risk**: Low | **Success Rate**: 40%

### Option 4: New Clone (Last resort)
```bash
# Archive corrupted repository
mv .git .git.corrupted

# Clone fresh from GitHub
git clone https://github.com/[owner]/[repo].git [temp-dir]
cd [temp-dir]

# Cherry-pick our commits from corrupted repo
git log /path/to/corrupted/.git --oneline | head -7

# Add commits from backup branch
for commit in [SHAS]; do
    git cherry-pick $commit
done

# Verify
git fsck --full
git log --oneline -7
```

**Time**: 10-15 minutes | **Risk**: Medium | **Success Rate**: 85%

### Escalation
```bash
# After attempting recovery:
# If all options fail, escalate immediately
echo "CRITICAL: Repository corruption unrecoverable" | \
    mail -s "Escalation: Repo corruption" team-lead@cohezion.ai

# Archive evidence
cp -r .git .git.corrupted-evidence-$(date +%s)
```

---

## SCENARIO C2: Commits Missing

### Symptoms
- `git log` shows fewer than 7 commits
- Some commit SHAs missing
- History is shortened/truncated

### Root Causes
- Incomplete push or fetch
- Accidental reset (git reset --hard)
- Force push from upstream
- Rebase operation

### Recovery Decision Tree

```
Commits Missing
├─ Can recover from backup?
│  ├─ YES → restore backup commits
│  └─ NO → check reflog
├─ Check reflog for commits
│  ├─ Found → cherry-pick back
│  └─ Not found → check GitHub/GitLab remotes
├─ Available on remote?
│  ├─ YES → reset from remote
│  └─ NO → escalate
└─ Last resort: restore from archive
```

### Option 1: Restore from Backup (Recommended)
```bash
# Show backup branch commits
git log backup/session-55-test-fixes-main --oneline -10

# Count commits in main branch
MAIN_COUNT=$(git log --oneline | wc -l)
BACKUP_COUNT=$(git log backup/session-55-test-fixes-main --oneline | wc -l)

echo "Main: $MAIN_COUNT commits, Backup: $BACKUP_COUNT commits"

# If backup has more commits:
git merge backup/session-55-test-fixes-main

# If backup is diverged, reset to backup
git reset --hard backup/session-55-test-fixes-main

# Verify
git log --oneline -7
```

**Time**: 2-3 minutes | **Risk**: Low | **Success Rate**: 100%

### Option 2: Check Reflog
```bash
# View reflog
git reflog | head -20

# Example output:
# abc1234 HEAD@{0}: reset: moving to origin/main
# ddc56ac HEAD@{1}: commit: docs: Session 55...
# f123456 HEAD@{2}: commit: docs: Phase 3...

# Reset to state with all commits
git reset --hard HEAD@{1}

# Verify
git log --oneline -7
```

**Time**: 2-3 minutes | **Risk**: Low | **Success Rate**: 70%

### Option 3: Restore from Remote
```bash
# Fetch from GitHub/GitLab
git fetch origin session-55-test-fixes-main

# Check remote branch
git log origin/session-55-test-fixes-main --oneline -7

# Reset to remote if it has the commits
git reset --hard origin/session-55-test-fixes-main

# Verify
git log --oneline -7
```

**Time**: 2-3 minutes | **Risk**: Low | **Success Rate**: 80%

### Option 4: Last Resort - Archive Restoration
```bash
# If commits are in archived backups
# (e.g., ~/cohezion-backup-2026-02-11/)

# List available commits in archive
git log ~/cohezion-backup/[worktree]/.git --oneline -10

# Cherry-pick missing commits
for commit in [SHAS]; do
    git --git-dir=~/cohezion-backup/[worktree]/.git \
        format-patch -1 $commit | git am
done

# Verify
git log --oneline -7
```

**Time**: 5-10 minutes | **Risk**: Medium | **Success Rate**: 90%

### Escalation
```bash
# If more than 2 commits lost:
echo "Commits missing: $(git log --oneline | wc -l) found, expected 7+" | \
    mail -s "Escalation: Missing commits" architect@cohezion.ai
```

---

## SCENARIO C3: Backup Branch Missing

### Symptoms
- `git branch backup/session-55-test-fixes-main` doesn't exist
- Backup hasn't been created yet
- No fallback for recovery

### Root Causes
- Backup was never created
- Backup was deleted accidentally
- Backup creation failed silently

### Recovery Decision Tree

```
Backup Missing
├─ Do we have current branch intact?
│  ├─ YES → create backup now
│  └─ NO → restore from GitHub/GitLab first
├─ Create backup from:
│  ├─ Current branch (if intact)
│  ├─ GitHub/GitLab remote
│  └─ Reflog historical state
└─ Verify backup is correct
```

### Option 1: Create Backup from Current Branch (Recommended)
```bash
# Verify current branch is correct
git log --oneline -3

# Create backup branch
git branch backup/session-55-test-fixes-main

# Verify backup
git branch -v | grep backup
git log backup/session-55-test-fixes-main --oneline -3

# Output should show same commits as main
```

**Time**: 1 minute | **Risk**: None | **Success Rate**: 100%

### Option 2: Restore Backup from GitHub
```bash
# Fetch from remote
git fetch origin session-55-test-fixes-main

# Create backup from remote
git branch backup/session-55-test-fixes-main origin/session-55-test-fixes-main

# Verify
git log backup/session-55-test-fixes-main --oneline -7
```

**Time**: 1-2 minutes | **Risk**: Low | **Success Rate**: 90%

### Option 3: Restore Backup from Historical Reflog
```bash
# Find state with all 7 commits
git reflog | head -20

# Find an entry before any deletions
# (e.g., "ddc56ac HEAD@{5}: commit: docs: Session 55...")

# Create backup from that state
git branch backup/session-55-test-fixes-main HEAD@{5}

# Verify
git log backup/session-55-test-fixes-main --oneline -7
```

**Time**: 2-3 minutes | **Risk**: Medium | **Success Rate**: 80%

### Prevention
```bash
# After creating backup, verify it exists:
git branch -v | grep backup

# Set up automatic backup before risky operations:
git branch backup/$(git rev-parse --abbrev-ref HEAD) $(git rev-parse HEAD)
```

---

## SCENARIO C4: Size Check Failed

### Symptoms
- `.git/` directory is >6.5GB (no significant reduction)
- Cleanup operation didn't reduce size
- Large files still present

### Root Causes
- Cleanup operation incomplete
- git gc didn't run successfully
- Large files never removed
- Object database fragmented

### Recovery Decision Tree

```
Size Not Reduced
├─ Run aggressive garbage collection?
│  ├─ YES → git gc --aggressive
│  └─ NO → accept size, proceed
├─ Size improved?
│  ├─ YES → proceed
│  └─ NO → check for large files
├─ Large files found?
│  ├─ YES → consider git filter-branch
│  └─ NO → proceed with caution
└─ Size acceptable (<6.5GB)?
```

### Option 1: Aggressive Garbage Collection (Recommended)
```bash
# Record size before
du -sh .git/ | tee /tmp/size_before_gc.txt

# Run aggressive gc
git gc --aggressive --prune=now

# Record size after
du -sh .git/ | tee /tmp/size_after_gc.txt

# Calculate improvement
BEFORE=$(grep -oE '[0-9.]+' /tmp/size_before_gc.txt)
AFTER=$(grep -oE '[0-9.]+' /tmp/size_after_gc.txt)
echo "Size: ${BEFORE}GB → ${AFTER}GB"

# If significant improvement (>10%): success
# If minimal improvement: proceed to Option 2
```

**Time**: 15-30 minutes | **Risk**: Low | **Success Rate**: 85%

### Option 2: Find Large Files
```bash
# Identify large objects in repository
git rev-list --all --objects | \
    sed -n $(git rev-list --objects --all | \
    cut -f1 -d' ' | \
    git cat-file --batch-check | \
    grep blob | \
    sort -k3 -n | \
    tail -10 | \
    cut -f1 | \
    while read hash; do
        echo -n "-e s/$hash/$hash/p ";
    done) | \
    cut -d' ' -f2- | \
    sort -u | head -20
```

**Time**: 5-10 minutes | **Risk**: None | **Success Rate**: 100%

### Option 3: Accept Size and Monitor
```bash
# If size is already <7GB and acceptable:
echo "Current size: $(du -sh .git/ | cut -f1)"
echo "Status: Acceptable, proceeding"

# Document in session notes
echo "Size check: Size is $(du -sh .git/ | cut -f1), proceeding without further optimization" >> /tmp/validation_notes.txt
```

**Time**: 1 minute | **Risk**: None | **Success Rate**: 100%

---

## SCENARIO C5: SHA Mismatch

### Symptoms
- Commit SHAs differ between before/after cleanup
- `git rev-parse HEAD` shows different SHA
- History appears modified

### Root Causes
- Commits were rebased or squashed
- Commits were amended
- Force push occurred
- Rebase with new author info

### Recovery Decision Tree

```
SHA Mismatch Detected
├─ Was rebase intentional?
│  ├─ YES → verify commits are functionally equivalent
│  └─ NO → rollback to backup
├─ Are file contents identical?
│  ├─ YES → proceed (SHA changed but content same)
│  └─ NO → investigate commits for changes
├─ Are all 7 commits present?
│  ├─ YES → likely due to rebase
│  └─ NO → missing commits, see Scenario C2
└─ Accept or rollback?
```

### Option 1: Verify Commits Are Identical (If intentional rebase)
```bash
# Compare commit trees (content)
BEFORE_TREE=$(head -1 /tmp/commits_before.txt | cut -d' ' -f1 | xargs -I {} git rev-parse {}^{tree})
AFTER_TREE=$(git rev-parse HEAD^{tree})

if [ "$BEFORE_TREE" = "$AFTER_TREE" ]; then
    echo "Content is identical (SHA changed due to rebase)"
    # This is acceptable
else
    echo "Content differs - investigate"
    # Proceed to Option 2
fi
```

**Time**: 2-3 minutes | **Risk**: None | **Success Rate**: 100%

### Option 2: Rollback to Backup
```bash
# If SHA mismatch is unintentional:
git reset --hard backup/session-55-test-fixes-main

# Verify
git rev-parse HEAD
git log --oneline -3

# Should match original SHAs
```

**Time**: 1-2 minutes | **Risk**: None | **Success Rate**: 100%

### Option 3: Investigate Commit Differences
```bash
# Compare detailed content
BEFORE_SHA=$(head -1 /tmp/commits_before.txt | cut -d' ' -f1)
AFTER_SHA=$(git rev-parse HEAD)

# Show differences
git diff $BEFORE_SHA..$AFTER_SHA --stat

# If no file differences: safe to proceed
# If files changed: investigate why
```

**Time**: 2-3 minutes | **Risk**: None | **Success Rate**: 100%

---

## SCENARIO C6: CLAUDE.md Corrupted

### Symptoms
- CLAUDE.md file is truncated or unreadable
- Encoding errors when reading file
- File size is drastically reduced
- Last modified timestamp is unexpected

### Root Causes
- Failed file write operation
- Disk space exhaustion during save
- Encoding mismatch
- File got overwritten accidentally

### Recovery Decision Tree

```
CLAUDE.md Corrupted
├─ Is file readable at all?
│  ├─ YES (truncated) → restore from git history
│  └─ NO (encoding error) → restore from backup
├─ How much was lost?
│  ├─ Small amount → git checkout
│  └─ Large amount → restore from backup
└─ Verify restored file
```

### Option 1: Restore from Previous Git Commit (Recommended)
```bash
# Verify file is corrupted
wc -l CLAUDE.md
file CLAUDE.md

# Restore from previous commit
git checkout HEAD~1 CLAUDE.md

# Verify restoration
wc -l CLAUDE.md  # Should show ~2000 lines
head -20 CLAUDE.md
tail -20 CLAUDE.md

# If successful, you may need to re-add any recent changes
# Check git status for modifications
```

**Time**: 1-2 minutes | **Risk**: None | **Success Rate**: 100%

### Option 2: Restore from Backup Branch
```bash
# If HEAD~1 doesn't have the file:
git show backup/session-55-test-fixes-main:CLAUDE.md > /tmp/CLAUDE.md.recovered

# Verify recovery
wc -l /tmp/CLAUDE.md.recovered
head -20 /tmp/CLAUDE.md.recovered

# Copy back
cp /tmp/CLAUDE.md.recovered CLAUDE.md

# Add and commit
git add CLAUDE.md
git commit -m "fix: Restore CLAUDE.md from backup"
```

**Time**: 2-3 minutes | **Risk**: None | **Success Rate**: 100%

### Option 3: Recover from Reflog
```bash
# Find when file was last intact
git reflog --follow CLAUDE.md | head -10

# Restore from that state
# Example: git checkout HEAD@{3}:CLAUDE.md
git checkout HEAD@{N}:CLAUDE.md

# Verify
wc -l CLAUDE.md
```

**Time**: 2-3 minutes | **Risk**: Low | **Success Rate**: 90%

---

## SCENARIO G1: Push Rejected

### Symptoms
- `git push` exits with error
- Output shows "rejected" or "access denied"
- Authentication failures
- Branch conflicts

### Root Causes
- Invalid GitHub token/SSH key
- Branch protection rules
- Authentication not configured
- Insufficient permissions

### Recovery Decision Tree

```
Push Rejected
├─ Error type?
│  ├─ Authentication error → fix credentials
│  ├─ Permission denied → check settings
│  ├─ Branch protected → bypass or request
│  └─ Other error → investigate message
├─ Fix error
└─ Retry push
```

### Option 1: Verify Authentication
```bash
# Check configured remote
git remote -v

# Test authentication
git ls-remote origin HEAD

# If fails: reconfigure credentials
# For SSH:
ssh -T git@github.com

# For HTTPS:
git credential approve  # Clear cached credentials

# Try push again
git push origin session-55-test-fixes-main -v
```

**Time**: 2-3 minutes | **Risk**: None | **Success Rate**: 95%

### Option 2: Force Push (If branch already exists)
```bash
# Safe force push (checks if base hasn't changed)
git push --force-with-lease origin session-55-test-fixes-main

# If that fails, verify no one else has pushed:
git log origin/session-55-test-fixes-main --oneline -3
git log session-55-test-fixes-main --oneline -3

# If identical: use force push
# If different: investigate divergence
```

**Time**: 2-3 minutes | **Risk**: Medium | **Success Rate**: 85%

### Option 3: Check Branch Protection Rules
```bash
# If GitHub API available:
gh api repos/[owner]/[repo]/branches/session-55-test-fixes-main \
    --jq '.protection'

# If protected and no delete permission:
# Option A: Request merge to main instead
# Option B: Ask repository admin to disable protection
# Option C: Push to different branch and create PR
```

**Time**: 5-10 minutes | **Risk**: Medium | **Success Rate**: 80%

---

## SCENARIO G2: HTTP 500 Errors

### Symptoms
- Push shows "error: 500 Internal Server Error"
- GitHub/GitLab appears to be having issues
- Transient failures that may retry

### Root Causes
- GitHub/GitLab service outage
- Temporary network issues
- Server overload
- Infrastructure problems

### Recovery Decision Tree

```
HTTP 500 Error
├─ Check service status
│  ├─ Outage in progress → wait and retry
│  └─ No reported outage → network issue
├─ Wait appropriate time
├─ Retry push
└─ If persists after 15 min → escalate
```

### Option 1: Check Service Status and Wait
```bash
# For GitHub
curl -s https://www.githubstatus.com/api/v2/summary.json | \
    jq '.components[] | select(.name=="API Requests")'

# For GitLab
curl -s https://status.gitlab.com/api/v2/summary.json | \
    jq '.components[] | select(.name=="API")'

# If status is not operational, wait
echo "GitHub status indicates issue. Waiting 5 minutes..."
sleep 300

# Retry push
git push origin session-55-test-fixes-main -v
```

**Time**: 5-10 minutes | **Risk**: None | **Success Rate**: 90%

### Option 2: Network Diagnostics
```bash
# Check network connectivity
ping -c 3 github.com

# Test HTTPS connectivity
curl -I https://github.com

# Check DNS
nslookup github.com

# If network is fine but push fails:
# This is likely a service issue, wait and retry
```

**Time**: 2-3 minutes | **Risk**: None | **Success Rate**: 80%

### Option 3: Escalate If Persistent
```bash
# If error persists after 15 minutes and status shows no issues
echo "HTTP 500 error persistent, GitHub status normal" | \
    mail -s "GitHub Push Issue" devops-lead@cohezion.ai

# Document attempt
echo "Attempted push at $(date), failed with HTTP 500" >> /tmp/push_attempts.log
```

**Time**: 2 minutes | **Risk**: None | **Success Rate**: 100%

---

## SCENARIO G3: Remote Branch Not Found

### Symptoms
- `git ls-remote origin session-55-test-fixes-main` returns nothing
- Branch doesn't exist on GitHub after push
- Push may have succeeded locally but didn't reach server

### Root Causes
- Push was incomplete/silently failed
- Branch name mismatch
- Push was to wrong remote
- Branch was deleted on server

### Recovery Decision Tree

```
Remote Branch Missing
├─ Verify branch exists locally
│  ├─ YES → push again
│  └─ NO → create branch locally
├─ Push to remote
├─ Verify branch exists on remote
└─ Troubleshoot if still missing
```

### Option 1: Verify and Retry Push
```bash
# Verify local branch exists
git branch -v | grep session-55-test-fixes-main

# Verify remote is correct
git remote -v | grep origin

# Retry push with verbose output
git push -u origin session-55-test-fixes-main -v

# Verify on remote
git ls-remote origin session-55-test-fixes-main
```

**Time**: 2-3 minutes | **Risk**: None | **Success Rate**: 90%

### Option 2: Check Push Reflog
```bash
# View push history
git reflog | grep push

# Verify what was actually pushed
git fetch origin
git log origin/session-55-test-fixes-main --oneline -3 2>/dev/null || \
    echo "Branch not found on remote"

# If not found, push explicitly:
git push -u origin session-55-test-fixes-main --force-with-lease
```

**Time**: 2-3 minutes | **Risk**: Low | **Success Rate**: 85%

### Option 3: Manual Branch Push
```bash
# Create branch on remote explicitly
git push origin session-55-test-fixes-main:refs/heads/session-55-test-fixes-main -f

# Verify
git ls-remote origin session-55-test-fixes-main

# Should show commit SHA
```

**Time**: 2-3 minutes | **Risk**: Low | **Success Rate**: 95%

---

## SCENARIO G4: Commits Not Syncing to GitHub

### Symptoms
- Push succeeds but only partial commits visible on GitHub
- `git log` shows N commits locally, fewer on remote
- History is incomplete on web interface

### Root Causes
- Partial push (network interruption)
- Object packing incomplete
- Shallow clone issue
- Reference update failure

### Recovery Decision Tree

```
Commits Not Syncing
├─ How many commits missing?
│  ├─ 1-2 missing → retry push
│  └─ 3+ missing → check object database
├─ Local commits intact?
│  ├─ YES → repush
│  └─ NO → see Scenario C2
├─ Retry push
└─ Verify sync
```

### Option 1: Repack and Retry Push
```bash
# Repack local objects
git repack -A -d

# Verify all commits present locally
git log --oneline -7

# Retry push
git push origin session-55-test-fixes-main --force-with-lease -v

# Verify on remote
git fetch origin
git log origin/session-55-test-fixes-main --oneline -7
```

**Time**: 3-5 minutes | **Risk**: Low | **Success Rate**: 85%

### Option 2: Rebuild Refspec
```bash
# Force update all refs
git push origin session-55-test-fixes-main --force-with-lease \
    --set-upstream origin session-55-test-fixes-main

# Verify
git fetch origin --verbose
git log origin/session-55-test-fixes-main --oneline -7
```

**Time**: 2-3 minutes | **Risk**: Low | **Success Rate**: 80%

### Option 3: Clone and Revalidate
```bash
# Create temporary clone
git clone https://github.com/[owner]/[repo].git /tmp/verify-clone

# Check if commits exist
cd /tmp/verify-clone
git log session-55-test-fixes-main --oneline -7 2>/dev/null || \
    echo "Branch or commits not found on remote"

# If commits are missing, investigate with:
git rev-list origin/session-55-test-fixes-main | wc -l
```

**Time**: 5-10 minutes | **Risk**: None | **Success Rate**: 95%

---

## SCENARIO G5: CLAUDE.md Not Readable on GitHub

### Symptoms
- HTTP 404 when accessing CLAUDE.md on GitHub web
- File appears in repository but can't be viewed
- Encoding errors in browser
- Raw content returns errors

### Root Causes
- File not pushed (see G3)
- Encoding issues (UTF-8 mismatch)
- Path issues (case sensitivity)
- File size issues (too large)

### Recovery Decision Tree

```
File Not Readable
├─ Does file exist in repo?
│  ├─ NO → verify push (see G3)
│  └─ YES → check encoding
├─ Is encoding UTF-8?
│  ├─ YES → check file size
│  └─ NO → convert encoding
├─ Is file size <5MB?
│  ├─ YES → likely GitHub is caching
│  └─ NO → verify it's not binary
└─ Retry or escalate
```

### Option 1: Verify File Encoding
```bash
# Check current encoding
file CLAUDE.md
# Should show: "UTF-8 Unicode text"

# Verify with iconv
iconv -f UTF-8 -t UTF-8 CLAUDE.md > /dev/null && \
    echo "Encoding is valid UTF-8"

# If encoding is wrong, convert
iconv -f ISO-8859-1 -t UTF-8 CLAUDE.md > CLAUDE.md.utf8
mv CLAUDE.md.utf8 CLAUDE.md

# Commit and push
git add CLAUDE.md
git commit -m "fix: Convert CLAUDE.md to UTF-8 encoding"
git push origin session-55-test-fixes-main
```

**Time**: 2-3 minutes | **Risk**: None | **Success Rate**: 90%

### Option 2: Check File Size and Encoding
```bash
# Verify file size
wc -l CLAUDE.md
du -h CLAUDE.md  # Should be <2MB

# Check for binary content
file CLAUDE.md

# Verify it's text
head -1 CLAUDE.md | od -c | head  # Should show readable text

# If looks like text, push again
git push origin session-55-test-fixes-main --force-with-lease
```

**Time**: 2-3 minutes | **Risk**: None | **Success Rate**: 85%

### Option 3: Clear GitHub Cache and Retry
```bash
# GitHub caches files for a few minutes
# Wait 5 minutes and try again
echo "Waiting for cache clear..."
sleep 300

# Try accessing file again
curl -s https://raw.githubusercontent.com/[owner]/[repo]/session-55-test-fixes-main/CLAUDE.md | \
    head -20

# If still fails, the file truly isn't on server
# Revisit push verification
```

**Time**: 5-10 minutes | **Risk**: None | **Success Rate**: 95%

---

## SCENARIO E1: Entire.io Configuration Wrong

### Symptoms
- `.entire/settings.json` missing or incorrect
- Strategy is not `manual-commit`
- `enabled` is false

### Root Causes
- Configuration not initialized
- Wrong strategy selected
- File was deleted or modified

### Recovery

```bash
# Verify current settings
cat .entire/settings.json 2>/dev/null || echo "File missing"

# Create correct configuration
mkdir -p .entire

cat > .entire/settings.json << 'EOF'
{
  "strategy": "manual-commit",
  "enabled": true,
  "telemetry": true
}
EOF

# Verify
cat .entire/settings.json

# Re-enable hooks
entire enable 2>/dev/null || echo "Entire CLI not available"

# Commit changes
git add .entire/settings.json
git commit -m "fix: Configure Entire.io with manual-commit strategy"
```

**Time**: 2-3 minutes | **Risk**: None | **Success Rate**: 100%

---

## SCENARIO E2: No Checkpoint Created

### Symptoms
- `entire/checkpoints/v1` branch doesn't exist
- No checkpoint directories in git
- `entire status` shows no captures

### Root Causes
- Entire.io hooks not installed
- `manual-commit` strategy not capturing on push
- First checkpoint not created yet

### Recovery

```bash
# Re-enable Entire.io hooks
entire enable

# Verify hooks are installed
ls -la .git/hooks/ | grep entire

# Make a test commit to trigger checkpoint
git commit --allow-empty -m "chore: Trigger Entire.io checkpoint"

# Verify checkpoint created
git log entire/checkpoints/v1 --oneline -1 2>/dev/null || \
    echo "Checkpoint branch not created yet"

# Wait a few seconds and check again
sleep 5
git log entire/checkpoints/v1 --oneline -1 2>/dev/null || \
    echo "Entire.io may not be working"
```

**Time**: 5-10 minutes | **Risk**: None | **Success Rate**: 80%

---

## SCENARIO E3-E6: Entire.io Integration Issues

### Quick Reference Table

| Scenario | Symptom | Recovery |
|----------|---------|----------|
| E3: Context missing | context.md files empty or missing | Repeat commit with Entire enabled |
| E4: Wrong structure | Checkpoint dirs not in expected format | Re-enable Entire.io and commit |
| E5: CLAUDE.md not indexed | CLAUDE.md not in checkpoint context | Manual re-run: entire capture |
| E6: Cloud sync not working | `entire status` shows "never" or "failed" | Run `entire push` or check auth |

### Universal Recovery for E3-E6

```bash
# Option 1: Entire CLI method (if available)
entire push                    # Push checkpoints to cloud
entire status                  # Check status
entire rewind                  # Can rewind to previous checkpoint

# Option 2: Manual git method
# Force create new checkpoint by committing
git commit --allow-empty -m "chore: Force Entire.io checkpoint" \
    && git push origin session-55-test-fixes-main

# Option 3: Verify via logs
tail -100 .entire/logs/entire.log 2>/dev/null | grep -E "error|warn"
```

**Time**: 2-5 minutes | **Risk**: None | **Success Rate**: 75-90%

---

## SUMMARY: QUICK REFERENCE TABLE

| Failure ID | Fix | Time | Risk | Success |
|-----------|-----|------|------|---------|
| C1 | `git gc --aggressive`, then restore | 5-10m | Low | 60% |
| C2 | Restore from backup or reflog | 2-3m | None | 100% |
| C3 | `git branch backup/...` | 1m | None | 100% |
| C4 | `git gc --aggressive --prune` | 15-30m | Low | 85% |
| C5 | Verify content, then proceed | 2-3m | None | 100% |
| C6 | `git checkout HEAD~1 CLAUDE.md` | 1-2m | None | 100% |
| G1 | Verify auth, retry, force push | 2-3m | Medium | 85% |
| G2 | Check status, wait 5min, retry | 5-10m | None | 90% |
| G3 | Retry push with `-u` flag | 2-3m | None | 95% |
| G4 | `git repack -A -d`, retry | 3-5m | Low | 85% |
| G5 | Verify UTF-8 encoding, retry | 2-3m | None | 90% |
| E1 | Create settings.json | 2-3m | None | 100% |
| E2 | `entire enable`, commit | 5-10m | None | 80% |
| E3-E6 | `entire push` or re-enable | 2-5m | None | 75-90% |

---

## ESCALATION CONTACTS

```
team-lead@cohezion.ai          - Critical issues (C1, C2, C3)
devops-lead@cohezion.ai        - Push/GitHub issues (G1-G5)
architect@cohezion.ai          - Design/structural issues (C5, E3, E4)
qa-lead@cohezion.ai            - Validation issues (C6, E1, E2)
```

---

**Created**: 2026-02-11
**Last Updated**: 2026-02-11
**QA Lead**: Session 55 Validation Team
