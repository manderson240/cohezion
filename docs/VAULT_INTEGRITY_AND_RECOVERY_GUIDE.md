# Cloud Vault Integrity & Recovery Guide

**Last Updated**: 2026-02-09
**Document Type**: Operational Runbook
**Audience**: Development team, CI/CD maintainers

---

## Quick Reference

### Vault Location
```bash
~/dev/cohezion/cloud-vault-mcp/vault/          # Main vault (git-tracked)
~/vaults/cohezion-vault/                       # Alternative location (if configured)
```

### Validation Scripts
```bash
python3 ~/dev/cohezion/scripts/vault_integrity_checker.py
python3 ~/dev/cohezion/scripts/vault_reference_analyzer.py
```

### Git Health Check
```bash
cd ~/dev/cohezion/cloud-vault-mcp/vault
git fsck --full
git log --oneline | head
```

---

## Part 1: Integrity Verification

### 1.1 Regular Health Checks

**Daily/Pre-commit**:
```bash
# Quick format check
python3 scripts/vault_integrity_checker.py | tail -20

# Reference validation
python3 scripts/vault_reference_analyzer.py | tail -20
```

**Weekly/Before Major Commits**:
```bash
# Full integrity scan
python3 scripts/vault_integrity_checker.py > vault_check.log
python3 scripts/vault_reference_analyzer.py > vault_refs.log

# Git health
cd cloud-vault-mcp/vault
git fsck --full
git log --oneline --graph --decorate --all | head -20
```

### 1.2 What to Look For

#### Format Issues (CRITICAL)
- Unclosed code blocks (odd number of ```)
- Mismatched brackets: `[text]` vs `[text`
- Invalid YAML frontmatter
- File encoding errors

**How to Fix**:
```bash
# Check single file
python3 -c "
import sys
with open(sys.argv[1]) as f:
    content = f.read()
    if content.count('```') % 2:
        print('ERROR: Unclosed code blocks')
    if content.count('[') != content.count(']'):
        print('ERROR: Mismatched brackets')
" filepath.md
```

#### Metadata Issues (MEDIUM)
- Missing date field in decisions
- Missing status field in experiments
- Inconsistent date format

**How to Fix**:
```bash
# Add missing metadata
# Edit file and add to frontmatter:
# ---
# date: 2026-02-09
# status: COMPLETE
# ---
```

#### Reference Issues (LOW-MEDIUM)
- Broken wikilinks `[[nonexistent-note]]`
- Missing linked files
- Orphaned documents

**How to Fix**:
```bash
# Find broken references
grep -r "^\[\[" cloud-vault-mcp/vault/*.md | \
  while read line; do
    note=$(echo "$line" | grep -o "\[\[[^\]]*\]\]" | tr -d '[]')
    if ! find . -name "*$note*" -type f | grep -q .; then
      echo "Broken: $note"
    fi
  done

# Create missing file or fix link
```

#### Git Issues (CRITICAL)
- Corrupted objects
- Detached HEAD
- Untracked stale changes

**How to Diagnose**:
```bash
cd cloud-vault-mcp/vault

# Check object integrity
git fsck --full

# Check HEAD status
git rev-parse HEAD
git branch -a

# Check working tree
git status
git diff --stat
```

### 1.3 Automated Health Check (CI/CD)

**Add to pre-commit hook**:
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check vault integrity
cd cloud-vault-mcp/vault

# Markdown format
python3 ../../scripts/vault_integrity_checker.py > /tmp/vault_check.log
if grep -q "Status: FAIL" /tmp/vault_check.log; then
    cat /tmp/vault_check.log
    exit 1
fi

# Git health
git fsck --full > /dev/null || exit 1

exit 0
```

---

## Part 2: Recovery Procedures

### 2.1 Common Recovery Scenarios

#### Scenario A: Single File Corrupted

**Symptom**: Can't read a file, encoding error, or format broken

**Recovery**:
```bash
cd ~/dev/cohezion/cloud-vault-mcp/vault

# Option 1: Restore from git
git checkout HEAD -- path/to/file.md

# Option 2: View history
git log -p path/to/file.md | head -100

# Option 3: Find last good version
git log --follow --oneline path/to/file.md
git show <commit>:path/to/file.md > file_backup.md
```

**Time to Recover**: < 1 minute

---

#### Scenario B: Multiple Files Lost

**Symptom**: Directory deleted, accidental `rm -rf`

**Recovery**:
```bash
cd ~/dev/cohezion/cloud-vault-mcp/vault

# List deleted files
git status

# Restore entire directory
git checkout HEAD -- decisions/
git checkout HEAD -- patterns/
# etc.

# Or restore all
git checkout HEAD -- .
```

**Time to Recover**: < 2 minutes

---

#### Scenario C: Git History Corrupted

**Symptom**: `git fsck` reports errors, can't read objects

**Recovery Priority**:
1. Stop all operations (prevent further corruption)
2. Create emergency backup of working files
3. Restore from known-good backup

**Steps**:
```bash
# Emergency backup of current state
cp -r cloud-vault-mcp/vault /tmp/vault_backup_$(date +%s)

# Option A: Fresh clone (if remote exists)
rm -rf cloud-vault-mcp/vault
git clone <remote> cloud-vault-mcp/vault

# Option B: Rebuild from backups
# Use external backup system (S3, NAS, etc.)

# Option C: Prune and recover
cd cloud-vault-mcp/vault
git gc --prune=now
git fsck --full
```

**Time to Recover**: 5-15 minutes (depends on corruption extent)

---

#### Scenario D: Vault Becomes Out of Sync

**Symptom**: Local changes don't match remote, merge conflicts

**Recovery**:
```bash
cd ~/dev/cohezion/cloud-vault-mcp/vault

# Show divergence
git log --oneline --graph --decorate --all | head -20

# Safe merge (preserves both histories)
git merge origin/main

# Or reset to remote if local is broken
git reset --hard origin/main
git pull
```

**Time to Recover**: < 5 minutes

---

### 2.2 Prevention Strategy

**Backup Schedule**:
- **Git**: Always available (distributed VCS)
- **External**: Daily export to S3 or NAS
- **Archive**: Weekly snapshot for long-term retention

**Backup Implementation**:
```bash
#!/bin/bash
# backup_vault.sh (run daily via cron)

VAULT_DIR="~/dev/cohezion/cloud-vault-mcp/vault"
BACKUP_DIR="/backups/vault/$(date +%Y-%m-%d)"

mkdir -p "$BACKUP_DIR"

# Git bundle (portable backup)
cd "$VAULT_DIR"
git bundle create "$BACKUP_DIR/vault.bundle" --all

# File export
tar czf "$BACKUP_DIR/vault-files.tar.gz" \
  --exclude=.git \
  "$VAULT_DIR"

# Verify backup
tar tzf "$BACKUP_DIR/vault-files.tar.gz" | head -20
```

---

## Part 3: Health Dashboard

### 3.1 Key Metrics

```
Vault Health Indicators
========================

Format Validity:      [████████████████████] 100% ✓
Metadata Consistency: [████████████████████] 100% ✓
Reference Integrity:  [████████████████████] 100% ✓
Git History:          [████████████████████] 100% ✓
Document Count:       [████░░░░░░░░░░░░░░░] 11/161 (awaiting Task #6)

Last Validation:      2026-02-09 09:00 UTC
Last Backup:          [To be configured]
Recovery Tested:      Not yet (recommended monthly)
```

### 3.2 Monitoring Command

```bash
# Real-time vault monitoring
watch -n 300 'python3 scripts/vault_integrity_checker.py | tail -10'

# Alert on failures
(cron job) python3 scripts/vault_integrity_checker.py | \
  grep "FAIL" && \
  mail -s "ALERT: Vault integrity failed" admin@cohezion.local
```

---

## Part 4: Data Integrity Standards

### 4.1 Markdown Standards

**Required Format**:
```markdown
---
date: YYYY-MM-DD
status: [DRAFT|COMPLETE|ARCHIVED]
[other-fields]
---

# Document Title

Content here...
```

**Validation**:
- Single H1 at top (# Title)
- Balanced code fences (```...```)
- Balanced brackets ([text](url))
- UTF-8 encoding
- LF line endings (not CRLF)

### 4.2 Metadata Standards

| Document Type | Required Fields | Example |
|---------------|-----------------|---------|
| decision | date, status | date: 2026-02-09, status: COMPLETE |
| experiment | date, status, result | date: 2026-02-09, status: COMPLETE |
| pattern | category | category: distributed-systems |
| project | status | status: ACTIVE |

### 4.3 Naming Conventions

**File Naming**:
- Format: `YYYY-MM-DD-title-in-kebab-case.md`
- Example: `2026-02-09-phase-5b-coordination.md`
- Avoid: CamelCase, spaces, underscores in main title

**Directory Structure**:
```
vault/
├── decisions/        # Architecture Decision Records
├── experiments/      # Experiment logs with results
├── patterns/         # Reusable solution patterns
├── projects/         # Project index/overview documents
├── daily/            # Daily development logs
└── papers/           # Literature notes
```

### 4.4 Cross-Reference Format

**Wikilinks** (Preferred):
```markdown
[[phase-5b-multi-agent-coordination]]
[[session-40-retrospective]]
```

**Markdown Links** (Fallback):
```markdown
[Phase 5B Overview](decisions/phase-5b-overview.md)
[Session 40](projects/SESSION-40-PHASE-5B-COMPLETION.md)
```

---

## Part 5: Troubleshooting Matrix

| Symptom | Cause | Solution | Time |
|---------|-------|----------|------|
| Can't read file | Encoding error | `git checkout HEAD -- file` | 1 min |
| Broken markdown | Syntax error | Fix with `vault_integrity_checker.py` | 5 min |
| Broken wikilinks | Missing file | Create file or fix link | 2 min |
| Git fsck error | Object corruption | `git gc --prune` then restore | 15 min |
| Out of sync | Merge needed | `git merge` or `git reset` | 5 min |
| Lost files | Accidental delete | `git checkout HEAD -- .` | 1 min |
| Performance slow | Too many files | Archive old docs | 30 min |
| MCP connection lost | Network/auth | Restart MCP server | 2 min |

---

## Part 6: CI/CD Integration

### 6.1 Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

cd cloud-vault-mcp/vault || exit 1

# Run integrity check
python3 ../../scripts/vault_integrity_checker.py 2>&1 | \
  grep -i "CRITICAL" && {
    echo "ERROR: Critical integrity issues found"
    exit 1
  }

# Check git health
git fsck --full > /dev/null 2>&1 || {
    echo "ERROR: Git corruption detected"
    exit 1
}

exit 0
```

### 6.2 Pre-push Hook

```bash
#!/bin/bash
# .git/hooks/pre-push

cd cloud-vault-mcp/vault || exit 1

# Prevent force push
while IFS=' ' read -r local_ref local_sha remote_ref remote_sha; do
    if [[ "$local_sha" != "0000000000000000000000000000000000000000" ]]; then
        if [[ "$remote_sha" != "0000000000000000000000000000000000000000" ]]; then
            # Check if this is a force push
            git merge-base --is-ancestor "$remote_sha" "$local_sha" || {
                echo "ERROR: Would rewrite remote history. Use with extreme caution."
                exit 1
            }
        fi
    fi
done

exit 0
```

### 6.3 GitHub Actions Validation

```yaml
# .github/workflows/vault-validation.yml
name: Vault Integrity Check

on:
  push:
    paths:
      - 'cloud-vault-mcp/vault/**/*.md'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: python3 scripts/vault_integrity_checker.py
      - run: |
          cd cloud-vault-mcp/vault
          git fsck --full
```

---

## Part 7: Escalation & Support

### 7.1 When to Escalate

| Situation | Action | Contact |
|-----------|--------|---------|
| File corrupted | Try restore, contact DevOps if fails | DevOps Lead |
| Git corruption | Follow recovery procedure, escalate | DevOps Lead |
| Reference broken (1-2) | Fix manually | Document Owner |
| Reference broken (10+) | Run repair script | Integration Lead |
| Cannot access vault | Check network, auth, MCP server | DevOps Lead |
| Performance degraded | Archive old docs, optimize | Architecture Lead |

### 7.2 Documentation Updates

After any incident:
1. Document what happened
2. Record recovery steps taken
3. Update this guide with new procedures
4. Notify team of lessons learned

---

## Appendix A: Recovery Testing Checklist

**Monthly Recovery Test** (Recommended):

```bash
# 1. List current state
cd ~/dev/cohezion/cloud-vault-mcp/vault
git log --oneline | head -5
echo "Files: $(find . -name '*.md' -type f | wc -l)"

# 2. Create test backup
cp -r . /tmp/vault_test_$(date +%s)

# 3. Simulate corruption
# (Don't actually corrupt in production!)

# 4. Test recovery
# See "Recovery Procedures" section

# 5. Verify restored state
cd /tmp/vault_test_*
python3 ../../scripts/vault_integrity_checker.py | grep Status

# 6. Clean up
rm -rf /tmp/vault_test_*

# 7. Document results
echo "Recovery test completed successfully" >> recovery_test_log.txt
```

---

## Appendix B: Related Scripts

### vault_integrity_checker.py
Location: `~/dev/cohezion/scripts/vault_integrity_checker.py`
- Validates markdown format
- Checks metadata consistency
- Analyzes git history
- Generates JSON report

### vault_reference_analyzer.py
Location: `~/dev/cohezion/scripts/vault_reference_analyzer.py`
- Analyzes cross-document references
- Detects orphaned documents
- Finds circular dependencies
- Identifies well-connected hubs

---

## Document History

| Date | Change | Author |
|------|--------|--------|
| 2026-02-09 | Initial version | Integrity Specialist |
| TBD | Recovery procedures tested | DevOps Lead |
| TBD | CI/CD integration complete | DevOps Lead |
| TBD | Backup system deployed | DevOps Lead |

---

**Last Review**: 2026-02-09
**Next Review**: 2026-03-09 (monthly)
**Status**: ACTIVE
