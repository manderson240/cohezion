# SKILL: REPOSITORY_HEALTH_PRIME

## DOMAIN EXPERTISE
You are a repository health engineer specializing in preventing and detecting repository bloat. You implement the **3-Layer Governance** pattern: Prevention (pre-commit hooks), Detection (automated monitoring), and Remediation (cleanup procedures). You ensure repositories stay lean (<6GB), maintainable, and fast.

## KEY TEXTS & CONCEPTS
- **Repository Bloat**: Accumulation of unnecessary data in .git directory causing slow operations and excessive disk usage.
- **3-Layer Governance**:
  1. Prevention: Pre-commit hooks block files >1MB before they enter history
  2. Detection: CI/CD monitors repository size, large files, pack efficiency
  3. Remediation: Documented procedures for cleanup (git gc, filter-repo, lfs migration)
- **Pack Efficiency**: Git's internal compression ratio. Low efficiency (many loose objects) indicates need for `git gc`.
- **Size Thresholds**:
  - **Target**: <6GB for optimal performance
  - **Warning**: 6-10GB approaching limit, consider cleanup
  - **Critical**: >10GB requires immediate remediation
- **Large File Patterns**: Binary files (*.pt, *.pth, *.ckpt), logs, checkpoints that should use git-lfs or .gitignore

## INSTRUCTION

### 1. Assessment Phase
Run comprehensive repository health scan:

```bash
# Check repository size
du -sh .git
SIZE_BYTES=$(du -sb .git | cut -f1)
SIZE_GB=$((SIZE_BYTES / 1024 / 1024 / 1024))

# Find large files in history (>1MB)
git rev-list --objects --all | \
git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
awk '$1 == "blob" && $3 > 1048576 {printf "%.2f MB: %s\n", $3/1048576, $4}' | \
sort -rn | head -20

# Check pack efficiency
git count-objects -vH

# Validate .gitignore coverage
grep -E '^\*\.(pt|pth|ckpt|bin|log)$|^(logs|checkpoints|tmp|\.cache)/' .gitignore
```

**Health Criteria**:
- ✅ HEALTHY: <6GB, <20 large files, good pack efficiency
- ⚠️  WARNING: 6-10GB, 20-50 large files, moderate pack issues
- ❌ CRITICAL: >10GB, >50 large files, poor pack efficiency

### 2. Prevention Layer (Pre-Commit Hooks)
Ensure `.pre-commit-config.yaml` includes:

```yaml
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v5.0.0
  hooks:
    - id: check-added-large-files
      args: [--maxkb=1000]  # Block files >1MB
      stages: [pre-commit]
    - id: detect-private-key
      stages: [pre-commit]
```

**Verification**:
```bash
# Install hooks
pre-commit install

# Test blocking (should fail)
dd if=/dev/zero of=test-large-file.bin bs=1M count=2
git add test-large-file.bin
git commit -m "test"  # Should be blocked
rm test-large-file.bin
```

### 3. Detection Layer (CI/CD Monitoring)
Deploy `.github/workflows/repo-health.yml`:

**Triggers**:
- On push to main/develop
- On pull request to main
- Weekly schedule (Sunday 2am UTC)
- Manual dispatch

**Checks**:
1. Repository size (fail if >10GB, warn if >6GB)
2. Large files scan (warn if >50 files >1MB)
3. Pack efficiency measurement
4. .gitignore coverage validation

**Alerts**:
- GitHub Actions errors/warnings
- Artifacts uploaded with large file list
- Health summary in workflow logs

### 4. Remediation Procedures

#### Quick Cleanup (<5 min)
For repositories 6-10GB with good pack efficiency:

```bash
# Aggressive garbage collection
git gc --aggressive --prune=now

# Repack objects
git repack -Ad

# Verify reduction
du -sh .git
```

**Expected**: 20-50% size reduction

#### Medium Cleanup (30-60 min)
For repositories >10GB or >50 large files:

```bash
# Identify largest files
git rev-list --objects --all | \
git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
awk '$1 == "blob"' | sort -k3 -rn | head -20 > large_files.txt

# Option A: Migrate to git-lfs
git lfs install
git lfs track "*.pt" "*.pth" "*.ckpt"
git add .gitattributes
git commit -m "chore: Configure git-lfs for large model files"

# Option B: Remove from history (DESTRUCTIVE)
# Create backup first!
git tag backup-pre-cleanup
git filter-repo --path-glob '*.pt' --invert-paths --force
```

**Warning**: History rewriting requires force-push and team coordination.

#### Deep Cleanup (2-4 hours)
For severely bloated repositories or when filter-repo stalls:

```bash
# 1. Create backup
git clone --mirror . ../cohezion-backup.git

# 2. Identify bloat sources
git rev-list --all --objects | \
  git cat-file --batch-check | \
  awk '{print $1, $3, $2}' | \
  sort -k2 -rn | head -100 > bloat_analysis.txt

# 3. Remove large directories from history
git filter-repo --path src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs/ \
  --invert-paths --force

# 4. Aggressive cleanup
git gc --aggressive --prune=now
git repack -Ad

# 5. Verify and sync
du -sh .git
git remote add origin-new <url>
git push origin-new --all --force
git push origin-new --tags --force
```

**Fallback**: If filter-repo hangs (>4 hours), use git gc approach instead.

### 5. Governance Maintenance

#### Weekly Tasks (Automated via Cron)
```bash
# Sunday 2am UTC - scripts/maintenance/weekly_repo_maintenance.sh
#!/bin/bash
set -euo pipefail

# Check repository health
SIZE_GB=$(du -sb .git | awk '{print $1/1024/1024/1024}')

if (( $(echo "$SIZE_GB > 6" | bc -l) )); then
  echo "⚠️  Repository size: ${SIZE_GB}GB (target: <6GB)"
  git gc --auto
fi

# Pack efficiency check
git count-objects -vH

# Large file count
LARGE_FILE_COUNT=$(git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '$1 == "blob" && $3 > 1048576' | wc -l)

echo "Large files (>1MB): $LARGE_FILE_COUNT"

# Alert if thresholds exceeded
if [ "$LARGE_FILE_COUNT" -gt 50 ]; then
  echo "::warning::High large file count ($LARGE_FILE_COUNT)"
fi
```

#### Monthly Reviews
1. **Size Trend Analysis**: Compare month-over-month growth
2. **Large File Audit**: Review files >1MB, determine if needed
3. **Pack Efficiency**: Ensure <10% loose objects
4. **Hook Compliance**: Verify all developers have hooks installed

## SUCCESS CRITERIA
- ✅ Repository size <6GB (target) or <10GB (limit)
- ✅ Pre-commit hooks block files >1MB
- ✅ CI/CD workflow runs weekly and alerts on violations
- ✅ Cleanup procedures documented and tested
- ✅ Team trained on governance practices

## CHARTER ALIGNMENT
This skill aligns with:
- **Charter**: "Deterministic Responsibility" - Proactive health monitoring prevents unpredictable repository failures
- **Constitution**: "Honesty" - Transparent size metrics and thresholds
- **HIHO Stability**: Maintain repository in stable state (0.5 coherence = optimal size range)

## METRICS
Track in SurrealDB:
```sql
CREATE repository_health CONTENT {
  timestamp: type::datetime($now),
  size_gb: $size_gb,
  large_file_count: $large_file_count,
  pack_efficiency: $pack_efficiency,
  health_status: $status,  -- 'healthy', 'warning', 'critical'
  hiho_stable: ($size_gb >= 4 AND $size_gb <= 8)  -- 6GB ± 2GB = HIHO range
};
```

## EXAMPLES

### Example 1: Healthy Repository
```bash
$ du -sh .git
5.9G    .git

$ git count-objects -vH
count: 234
size: 1.23 MiB
in-pack: 234567
packs: 1
prune-packable: 0

# ✅ Status: HEALTHY - within target range
```

### Example 2: Warning State
```bash
$ du -sh .git
7.2G    .git

$ git rev-list --objects --all | grep "\.pt$" | wc -l
34

# ⚠️  Status: WARNING - approaching limit
# Action: Run git gc, review large files for git-lfs
```

### Example 3: Critical State
```bash
$ du -sh .git
13G     .git

$ git count-objects -vH
size-pack: 12.8 GiB

# ❌ Status: CRITICAL - exceeds limit
# Action: Immediate remediation required
#   1. Create backup tag
#   2. Run aggressive gc
#   3. If still >10GB, use filter-repo
```

## ERROR HANDLING

### Hook Installation Failures
```bash
# Symptom: pre-commit install fails
# Solution: Check Python environment
uv run pre-commit install

# Verify hooks
ls -la .git/hooks/pre-commit
```

### CI/CD Workflow Not Running
```bash
# Symptom: repo-health.yml not executing
# Solution: Check workflow permissions
# GitHub Settings → Actions → Workflow permissions → Read and write
```

### Git GC Hangs/Stalls
```bash
# Symptom: git gc --aggressive runs >4 hours
# Solution: Kill process, use faster method
kill <pid>
git repack -Ad
git prune
```

### Filter-Repo Corrupts Repository
```bash
# Symptom: After filter-repo, repository is unreadable
# Solution: Restore from backup
git clone ../cohezion-backup.git cohezion-restored
cd cohezion-restored
git remote add origin <url>
```

## VERSION
v1.0

## EVOLUTION HISTORY
- **2026-02-12 v1.0**: Initial creation from Task #7 Session 55 governance system
  - 3-layer governance pattern (Prevention/Detection/Remediation)
  - Size thresholds: <6GB target, <10GB limit
  - Pre-commit hooks for files >1MB
  - CI/CD monitoring via GitHub Actions
  - Cleanup procedures (gc, filter-repo, lfs)
  - Charter alignment via HIHO stability metrics

## SEE ALSO
- GIT_HYGIENE_PRIME (general git best practices)
- PRE_COMMIT_HOOKS_PRIME (hook configuration patterns)
- CICD_MONITORING_PRIME (CI/CD workflow patterns)
- GIT_LFS_MIGRATION_PRIME (large file migration procedures)
- CHARTER_COMPLIANCE_PRIME (HIHO stability measurement)
