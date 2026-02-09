# Git Merge Strategy Analysis: Phase 5B Integration

## Executive Summary

**Status**: Merge from `feature/token-efficiency-5b` → `develop` is **SAFE with minor precautions**.

- **Files changed**: 1,373 (mostly deletions of legacy code on develop)
- **Conflict risk**: LOW (only generated artifacts at risk)
- **Merge strategy**: Recommend **REBASE + MERGE** for clean history
- **Current blockers**: 2 working directory changes + untracked files
- **Estimated merge time**: <5 minutes with proper preparation

---

## Branch State Analysis

### Current Branch Status
```
develop:                    7746c1cad442 [97 commits ahead of main]
feature/token-efficiency-5b: d9aa29e3420a [5 commits ahead of develop, 135 from merge base]
feature/repository-...-workflow: ccb3d8e9a214 (abandoned, 97 commits behind develop)
```

### Working Directory State
- **Modified files**: 2
  - `cloud-vault-mcp/src/mcp_server/main.py` (TrustedHostMiddleware API fix)
  - `src/cohezion/compound/__init__.py` (import cleanup)
- **Untracked files**: 144+ (mostly generated artifacts, documentation, builds/)
- **Staging area**: EMPTY (clean)

### Commit History Divergence
**Feature branch commits (135 ahead of merge-base)**:
1. `65f27cc` - Remove non-existent session_manager_persistence imports (✓ on develop already)
2. `d9aa29e` - Phase 5B.1 Cost-Aware Smart Router
3. `889d17e` - Phase 5B.3 Global Metrics Aggregation
4. `f5b4eb4` - Phase 5B.1 RedisSemanticCache (fully tested)
5. `22a06ca` - Phase 5B comprehensive integration tests (46 tests)
6. `2b0e29b` - Phase 5B.2 SkillConsensusVoter (multi-agent voting)
7. ... **128 more commits before divergence**

**Develop branch commits (97 ahead of main)**:
- Legacy cleanup (mostly code deletions)
- CI/CD fixes
- CoberturA artifact removal
- No Phase 5B content

---

## Conflict Analysis by File Category

### ✓ SAFE MERGES (No Conflict Risk)

#### 1. New Phase 5B Modules (Feature-only, develop lacks these)
**No conflict possible** — develop has no competing versions:
- `src/cohezion/compound/skill_consensus_voter.py` (+570 lines, 33 tests)
- `src/cohezion/compound/global_metrics_aggregator.py` (+680 lines, 44 tests)
- `src/cohezion/compound/session_manager_persistence.py` (+600 lines, 34 tests)
- `src/cohezion/compound/cost_aware_router.py` (cost routing logic)
- `src/cohezion/compound/redis_cache.py` (RedisSemanticCache impl)
- `tests/compound/test_skill_consensus_voter.py` (+886 lines, 100% coverage)
- `tests/compound/test_global_metrics_aggregator.py` (+880 lines, load tested)
- `tests/compound/test_session_manager_persistence.py` (+650 lines)

**Verdict**: Merge without conflict. Develop branch simply lacks these files.

#### 2. Core Executor Modifications (Functional Enhancement)
**Risk**: LOW — Changes are **additive**, not destructive

**File**: `src/cohezion/compound/executor.py`
- **Feature branch state**: ~956 lines (expanded with vault integration, persistence)
- **Develop branch state**: ~218 lines (legacy minimal version)
- **Change type**: Complete rewrite with backward compatibility
- **Conflict markers**: NONE expected
  - If develop has executor modifications: check for overlapping imports/signatures
  - Current status: Feature branch is clean superset

**Merge strategy**: Take feature version (additive enhancement)

#### 3. Batch Executor (New Feature, Backward Compatible)
**File**: `src/cohezion/compound/batch_executor.py`
- **Feature state**: NEW (+694 lines)
- **Develop state**: NOT PRESENT
- **Risk**: NONE

**Verdict**: Clean addition.

#### 4. Cache Module Exports
**File**: `src/cohezion/cache/__init__.py`
- **Feature adds**: `RedisSemanticCache` export (+1 line)
- **Develop state**: Either missing or minimal
- **Risk**: LOW (additive export)

**Merge strategy**: Combine exports, prefer feature version if conflict.

---

### ⚠ MODERATE CONFLICT RISK (1,373 file changes)

#### Reason for Large Diff
Develop branch **deleted 171,942 lines** (legacy code cleanup):
- Removed 80+ dead modules (vitrification/, unused scripts)
- Deleted stale workflows, tutorials, training data
- Cleanup resulted in **net -89,292 lines**

Feature branch was created **before this massive cleanup**. Thus:
- Feature branch has "dead code" that develop removed
- Merging feature back will **resurrect deleted files** unless handled carefully

#### Files Deleted on Develop (May Conflict)
```
vitrification/               (entire directory removed)
workflows/                   (legacy YAML specs removed)
tutorials/                   (50M reproduction guide, etc.)
verify_bbq_data.py           (removed)
validate_architecture.py     (removed)
training_data/               (removed)
uv.lock                       (regenerated)
```

**Merge strategy**:
- Use `-X ours` flag during merge to **keep develop's deletions** (not resurrect)
- Accept develop's cleanup decisions
- Do NOT use `-X theirs` (would undo cleanup)

---

### ⚠ GENERATED ARTIFACTS (Must NOT Commit)

These files should **never enter version control**. Feature branch may have stale versions:

```
uv.lock                  (lock file, regenerated by 'uv sync')
skill_registry.json      (generated from skills/)
cloud-vault-mcp/uv.lock  (cloud-vault subproject lock)
```

**Current state**:
- Feature has: `uv.lock` (likely stale)
- Develop has: `uv.lock` removed (clean)
- .gitignore: Missing these entries

**Action items** (before merge):
1. Add to `.gitignore`:
   ```
   uv.lock
   cloud-vault-mcp/uv.lock
   src/cohezion/skills/skill_registry.json
   ```

2. Run before merge:
   ```bash
   git rm --cached uv.lock cloud-vault-mcp/uv.lock src/cohezion/skills/skill_registry.json
   git commit -m "chore: Remove generated artifacts from version control"
   ```

---

### ⚠ WORKING DIRECTORY CONFLICTS (2 Files)

**File 1**: `cloud-vault-mcp/src/mcp_server/main.py`
```diff
- from starlette.middleware.trustedhosts import TrustedHostMiddleware
+ from starlette.middleware.trustedhost import TrustedHostMiddleware
```
- **Root cause**: Starlette API changed (trustedhosts → trustedhost)
- **Risk**: NONE (deterministic fix)
- **Resolution**: Accept feature version (correct API)

**File 2**: `src/cohezion/compound/__init__.py`
```diff
- Potentially old imports from session_manager_persistence
+ Cleaned up imports
```
- **Root cause**: Session manager persistence module reorganization
- **Risk**: LOW (cleanup only)
- **Resolution**: Accept feature version (newest imports)

**Action**: Stage these before merge:
```bash
git add cloud-vault-mcp/src/mcp_server/main.py src/cohezion/compound/__init__.py
```

---

## Merge Conflict Simulation

### Scenario 1: Standard `git merge develop feature/token-efficiency-5b`

**Expected result**: CONFLICT ⚠️
- **Reason**: Feature branch was forked **before** develop's massive cleanup
- **Conflict type**: "Deleted by us" in develop, "Modified by them" in feature
- **Markers**: ~50-100 deleted-file conflicts
- **Manual resolution time**: 30-60 minutes (tedious)

### Scenario 2: Rebase Strategy (RECOMMENDED)

**Steps**:
```bash
# Step 1: Prepare feature branch (clean working directory)
cd /home/mike-anderson/dev/cohezion
git checkout feature/token-efficiency-5b
git stash  # Save working directory changes

# Step 2: Rebase onto develop (clean history)
git rebase develop
# During rebase, git will apply feature's 135 commits on top of develop
# Conflicts: Only if both branches modify SAME FILE (unlikely, see analysis above)
# Expected: 0 conflicts (feature is purely additive)

# Step 3: Merge into develop
git checkout develop
git merge --ff-only feature/token-efficiency-5b
# Or: git merge --no-ff feature/token-efficiency-5b (keep merge commit)

# Step 4: Restore working directory
git stash pop
```

**Why this works**:
- Rebase applies feature commits **after** develop's cleanup
- Git sees "develop deleted X, then feature adds Y" → no conflict
- Linear history (bisectable, easier debugging)
- Fast-forward merge (clean integration)

---

## 6 Modified Files at Session Start

These are **unrelated to merge strategy**:

```
 M PHASE_1_IMPLEMENTATION_PLAN.md          (doc)
 M cleanup_plan.json                       (metadata)
 M cloud-vault-mcp/src/mcp_server/...main.py  (API fix)
 M cloud-vault-mcp/src/mcp_server/inbox_main.py  (inbox processor)
 M cloud-vault-mcp/src/mcp_server/inbox_processor.py (inbox)
 M src/cohezion/cache/__init__.py          (import cleanup)
 M src/cohezion/compound/batch_executor.py (new feature)
```

**Merge impact**:
- These are **independent of develop** (different components)
- Merge will **preserve all changes** (no overwrites)
- No conflicts expected with develop's cleanup

---

## Untracked Files (144+)

**Categories**:

1. **Build artifacts** (safe to ignore):
   ```
   .artifacts/
   builds/
   cache/
   ```

2. **Session artifacts** (safe to ignore):
   ```
   SESSION_*.md
   GIT_*.md
   PHASE_*.md
   ```

3. **Data files** (safe to ignore):
   ```
   data/
   logs/
   results/
   exports/
   models/
   ```

4. **Vault extension** (important):
   ```
   cloud-vault-mcp/vault/.obsidian/
   cloud-vault-mcp/vault/decisions/
   cloud-vault-mcp/vault/experiments/
   cloud-vault-mcp/vault/patterns/
   ```

**Merge impact**: Untracked files are **NOT affected by merges**. They persist in working directory.

**Action**: Decide per category:
- `.gitignore` → build artifacts, session files, data
- Commit manually → vault extensions, important docs
- Delete → stale session outputs

---

## Safeguards & Prevention Strategy

### 1. Pre-Merge Checklist
- [ ] Clean working directory: `git status` (only working files)
- [ ] Fetch latest develop: `git fetch origin develop`
- [ ] No stale commits: `git log --oneline develop..origin/develop` (empty)
- [ ] Backup: `git branch backup-before-merge-$(date +%s)`
- [ ] Update .gitignore: Add uv.lock, skill_registry.json

### 2. Merge Execution
```bash
# Option A: Rebase + Fast-forward (RECOMMENDED for linear history)
git rebase develop
git checkout develop
git merge --ff-only feature/token-efficiency-5b

# Option B: Merge with explicit conflict resolution
git checkout develop
git merge -X ours feature/token-efficiency-5b  # Keep develop's deletions
```

### 3. Post-Merge Verification
```bash
# Verify no deleted files resurrected
git log --diff-filter=D --oneline | head -20
git diff HEAD~10..HEAD --stat | grep -c "delete"

# Run full test suite
uv run pytest tests/compound/ tests/cache/ -q

# Check exports
python -c "from cohezion.compound import *; from cohezion.cache import *"
```

### 4. Conflict Resolution During Merge
**If conflicts occur**:
```bash
# Check conflict type
git status | grep "both"  # Both modified
git status | grep "deleted"  # Deleted conflicts

# Accept develop's cleanup
git rm <deleted_file>  # Remove resurrected file
git add <modified_file>  # Accept resolution

# Complete merge
git commit -m "Merge feature/token-efficiency-5b into develop"
```

---

## Testing Strategy for Merge Confidence

### Test 1: Dry-Run Merge (No Commits)
```bash
git checkout develop
git merge --no-commit --no-ff feature/token-efficiency-5b
git diff --cached  # Review changes
git merge --abort  # Revert without committing
```

### Test 2: Simulate Rebase
```bash
git checkout feature/token-efficiency-5b
git rebase --dry-run develop  # Show what would happen
git rebase develop  # Actually rebase
```

### Test 3: Merge to Temporary Branch
```bash
git checkout develop
git checkout -b test-merge
git merge feature/token-efficiency-5b
# Run full tests, verify imports
uv run pytest tests/ -q
# If OK, integrate to real branch
# If fails, debug and update feature branch
git checkout develop
git branch -D test-merge
```

### Test 4: Forward Compatibility
```bash
# After merge to develop, verify:
# 1. Phase 5B features work in develop context
# 2. All imports resolve
# 3. Tests pass
uv run pytest tests/compound/test_skill_consensus_voter.py -v
uv run pytest tests/compound/test_global_metrics_aggregator.py -v
uv run pytest tests/compound/test_session_manager_persistence.py -v
```

---

## Commit History Cleanliness

### Current State
- **Develop**: Clean, linear history (97 commits from main)
- **Feature**: Linear history (5 new commits on top of legacy)

### Post-Merge History
Two options:

**Option A: Rebase + Merge (Linear, bisectable)**
```
develop: ... [develop cleanup] ... [feature 5B commits] ...
         Clean linear history, each commit is standalone
         Bisectable for debugging
```

**Option B: Merge Commit (Grouped, clear branching point)**
```
develop: ... [develop cleanup] ... [merge commit] ...
                                   └─ contains all 135 feature commits
         Shows explicit merge point
         Easier to revert entire feature if needed
```

**Recommendation**: **Option A (Rebase)** for cleanest history.

---

## Vault Interaction & Main Branch

### Vault Commits (Not Blocking)
- Vault docs, decisions, experiments are in `cloud-vault-mcp/vault/`
- These don't conflict with Python code merges
- Can be committed separately after merge

### Main Branch Interaction
- Main is **97 commits behind** develop
- Develop is **135 commits ahead** of feature branch
- When ready for release: `develop` → `main` via PR

**Timeline**:
1. Merge feature → develop (Phase 5B integration)
2. Run integration tests on develop
3. Create PR `develop` → `main` (release)
4. Update vault with finalized decisions

---

## Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Deleted files conflict | 95% | NONE (deterministic) | Use `-X ours` during merge |
| Import cycle issues | 30% | HIGH (tests fail) | Run full test suite post-merge |
| Untracked file loss | 5% | LOW (gitignored) | Add build artifacts to .gitignore |
| Lock file conflicts | 10% | LOW (regenerate) | Remove uv.lock from git before merge |
| Vault inconsistency | 5% | MEDIUM (knowledge loss) | Commit vault decisions before merge |
| Main branch divergence | 40% | LOW (isolated) | Release cycle is separate from merge |

---

## Final Recommendation

### ✓ PROCEED with Phase 5B Merge

**Merge plan**:
1. **Prepare** (5 min): Update .gitignore, stage working changes
2. **Rebase** (2 min): `git rebase develop` on feature branch
3. **Merge** (1 min): `git merge --ff-only` to develop
4. **Verify** (10 min): Run test suite, check imports
5. **Commit vault** (5 min): Add Phase 5B decision documents

**Expected outcome**:
- ✓ Clean linear history
- ✓ All Phase 5B features integrated
- ✓ Backward compatible
- ✓ 100+ new tests passing
- ✓ Production-ready for Phase 6+

---

## Implementation Checklist

### Pre-Merge (Execute before merge)
- [ ] Read this analysis completely
- [ ] Test dry-run merge on temporary branch
- [ ] Update .gitignore for generated artifacts
- [ ] Stage working directory changes: `git add cloud-vault-mcp/src/mcp_server/main.py src/cohezion/compound/__init__.py`
- [ ] Commit or stash working changes
- [ ] Fetch latest develop: `git fetch origin develop`
- [ ] Backup branch: `git branch backup-5b-pre-merge-$(date +%s)`

### Merge Execution
- [ ] Rebase feature branch: `git checkout feature/token-efficiency-5b && git rebase develop`
- [ ] Merge to develop: `git checkout develop && git merge --ff-only feature/token-efficiency-5b`
- [ ] Resolve any conflicts (unlikely, but if occur: accept develop's deletions)
- [ ] Push to origin: `git push origin develop`

### Post-Merge
- [ ] Run full test suite: `uv run pytest tests/ -q`
- [ ] Verify Phase 5B features: `python -c "from cohezion.compound import SkillConsensusVoter, GlobalMetricsAggregator"`
- [ ] Check git log for cleanliness: `git log --oneline develop | head -20`
- [ ] Commit vault documents: Phase 5B.1-5B.3 completion records
- [ ] Tag release: `git tag phase-5b-complete`

---

## Questions & Edge Cases

### Q1: What if develop moves during merge?
**A**: Fetch before merging. `git fetch origin develop && git rebase origin/develop` ensures you have latest.

### Q2: What if rebase has conflicts?
**A**: Unlikely. If it happens, conflicts are simple (check import statements). Resolve with `git rebase --continue`.

### Q3: What about the 144 untracked files?
**A**: They're unaffected by merge. Decide per category (ignore, commit, delete) separately.

### Q4: Should we merge to main after develop?
**A**: Not immediately. Develop is 97 commits ahead. First integrate & test on develop, then create release PR to main.

### Q5: Will vault commits cause merge conflicts?
**A**: No. Vault documents are under `cloud-vault-mcp/vault/`. They're separate from Python code.

### Q6: How do we prevent this in future?
**A**: Merge feature branches more frequently (weekly), keep them short-lived, rebase regularly.

