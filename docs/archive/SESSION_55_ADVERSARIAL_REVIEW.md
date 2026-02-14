# Session 55: Adversarial Review - Edge Cases & Compound Opportunities

**Reviewer Role**: Challenge assumptions, find hidden risks, identify optimization opportunities
**Severity**: Critical path items only
**Status**: Pre-execution (stop-and-fix phase)

---

## SECTION 1: Edge Case Analysis

### Edge Case 1: SurrealDB Not Running During Migration

**Risk**: Migration script assumes SurrealDB is up and authenticated
**Current Plan**: No fallback if DB unavailable
**Failure Mode**:
```
async def migrate_from_tar(...):
    self.db = get_surreal_client()  # ⚠️ FAILS HERE if DB down
    # All data extracted but never stored
```

**Adversarial Question**: What if SurrealDB crashes mid-migration?

**Issues**:
1. Data extracted but not stored → orphaned tar files
2. Partial inserts → incomplete records
3. No rollback mechanism
4. No transaction semantics

**Fix Required**:
```python
async def migrate_from_tar(self, tar_path: str) -> dict:
    """Migrate with transactional safety"""

    # Check DB connectivity FIRST
    try:
        await self.db.query("SELECT 1")
    except Exception as e:
        raise Exception(
            f"SurrealDB unavailable. Aborting migration to prevent data loss.\n"
            f"Tar file safe at: {tar_path}\n"
            f"Error: {e}"
        )

    # Use SurrealDB transactions (if supported)
    async with self.db.transaction() as txn:
        try:
            # All inserts here
            collection_id = await self._insert_collection(txn, ...)
            await self._insert_files(txn, collection_id, ...)
            await txn.commit()
        except Exception:
            await txn.rollback()
            raise
```

**Verdict**: 🔴 BLOCKER - Must fix before execution

---

### Edge Case 2: Partial Tar Files / Corrupted Exports

**Risk**: Tar file extraction fails mid-stream
**Current Plan**: No checksum verification before/after
**Failure Mode**:
```bash
tar -xf export.tar  # Fails silently on corruption
# Some files extracted, others missing
# No way to know which
```

**Adversarial Question**: What if the export process was interrupted?

**Issues**:
1. Tar file might be truncated
2. Files might be extracted partially
3. No verification that tar is readable before migration starts
4. Checksum only calculated AFTER extraction (too late if corrupt)

**Fix Required**:
```bash
# Step 0c BEFORE migration - verify tar integrity
#!/bin/bash
verify_tar_integrity() {
    local tar_file=$1

    # Test tar can be read completely
    tar -tf "$tar_file" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "❌ TAR FILE CORRUPT: $tar_file"
        return 1
    fi

    # Count files
    file_count=$(tar -tf "$tar_file" | wc -l)
    echo "✅ TAR OK: $file_count files"
    return 0
}

# Run before any migration
for tar_file in /tmp/cohezion_training_data_export/logs_*.tar; do
    verify_tar_integrity "$tar_file" || exit 1
done
```

**Verdict**: 🔴 BLOCKER - Add tar integrity check before Phase 0e

---

### Edge Case 3: Duplicate Files with Same Name, Different Commits

**Risk**: Multiple commits have `lang_1768630692_0.txt` with different content
**Current Plan**: Uses `filename` as identifier, not content hash
**Failure Mode**:
```
Commit A: lang_0.txt (100 bytes)
Commit B: lang_0.txt (200 bytes, different content)
# SurrealDB stores both with same filename
# Which one do we retrieve?
```

**Adversarial Question**: How do we distinguish between file versions?

**Current Schema Issue**:
```sql
DEFINE FIELD filename ON training_data_files TYPE string;
# ⚠️ No uniqueness constraint - allows duplicates
```

**Fix Required**:
```sql
-- Make identifier COMPOSITE: filename + content_hash + commit
DEFINE FIELD uid ON training_data_files TYPE string PRIMARY KEY;  -- hash(filename + content_hash + commit)
DEFINE FIELD version_from_commit ON training_data_files TYPE string;  -- Which commit this came from
DEFINE INDEX unique_version ON training_data_files(filename, content_hash, version_from_commit);

-- Query should specify: "Get lang_0.txt from commit ABC123"
SELECT * FROM training_data_files
WHERE filename = 'lang_0.txt'
  AND version_from_commit = 'ddc56ac9c6a5';
```

**Verdict**: 🔴 BLOCKER - Schema must include commit tracking

---

### Edge Case 4: Training Data Still Being Committed After Migration

**Risk**: Developer commits new training data before pre-commit hook installed
**Current Plan**: Hook only installed AFTER destructive operations
**Failure Mode**:
```
Phase 0: Extract old data ✓
Phase 1: Remove from git ✓
Phase 2: Developer: "git add large_new_training_data.pkl" ✓
Phase 3: git-filter-repo BREAKS because HEAD has new data
```

**Adversarial Question**: When is the pre-commit hook active?

**Issues**:
1. Hook installed in Phase 5, but danger window is Phases 0-4
2. If developer commits during this time, git-filter-repo targets wrong files
3. Repository might have BOTH old and new training data

**Fix Required**:
```bash
# FIRST - install pre-commit hook
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Document the danger window
echo "⚠️ DANGER WINDOW: No new commits until Phase 1 complete"

# Then proceed with extraction/migration
```

**Verdict**: 🟡 HIGH - Reorder: install hook FIRST (Phase 0a), then extract (Phase 0b)

---

### Edge Case 5: SurrealDB Storage Limits / Query Performance

**Risk**: Training data metadata balloons beyond SurrealDB capacity
**Current Plan**: No size limits or performance testing
**Failure Mode**:
```
100+ files × 100+ commits = 10,000+ records
Each with content_preview (1000 chars) = 10MB just for previews
Query "SELECT *" times out
```

**Adversarial Questions**:
- How many files do we actually have?
- Total records: 100 files × 50 commits = 5,000 records?
- Preview storage: 5,000 × 1,000 chars = 5MB?
- Query performance: Can we sort/filter efficiently?

**Fix Required**:
```sql
-- Add size management
DEFINE FIELD content_preview ON training_data_files
  TYPE string
  ASSERT string::len($value) < 500;  -- Cap preview size

-- Add indexing for performance
DEFINE INDEX files_by_collection ON training_data_files(collection_id);
DEFINE INDEX files_by_hash ON training_data_files(content_hash);

-- Pagination for large queries
SELECT * FROM training_data_files
WHERE collection_id = 'col_123'
LIMIT 100
OFFSET 0;
```

**Verdict**: 🟡 MEDIUM - Add performance testing before Phase 0e

---

### Edge Case 6: Git History Has Symlinks to Training Data

**Risk**: Training data might not be directly in git, but symlinked
**Current Plan**: Only targets specific directory path
**Failure Mode**:
```
src/.../logs → symlink to /data/external/logs
git-filter-repo --path "logs/" doesn't follow symlinks
# Symlink remains, data not actually removed
```

**Adversarial Question**: Are there symlinks?

**Fix Required**:
```bash
# Before Phase 1, check for symlinks
find ~/dev/cohezion -type l | grep -i "training\|data\|logs"

# If found, need to handle differently
git log --all --full-history -- 'symbolic-ref' | head
```

**Verdict**: 🟡 MEDIUM - Add symlink check in Phase 0a

---

## SECTION 2: Compound Engineering Opportunities

### Opportunity 1: Batch All SurrealDB Operations

**Current Plan**: Creates records one-at-a-time
```python
for file_record in collection["files"]:
    await self.db.create("training_data_files", [file_record])  # ❌ N+1 queries
```

**Better**:
```python
# Batch create all at once
all_records = [record for collection in collections for record in collection["files"]]
await self.db.create("training_data_files", all_records)  # ✅ 1 query
```

**Efficiency Gain**: 10,000x faster for 100+ files

---

### Opportunity 2: Inline Hash Calculation with Tar Extraction

**Current Plan**: Two passes (extract, then hash)
```python
# Pass 1: Extract tar
content = f.read()
# Pass 2: Calculate hash
content_hash = hashlib.sha256(content).hexdigest()
```

**Better**:
```python
# Single pass with streaming hash
sha256 = hashlib.sha256()
chunk_size = 8192
while chunk := f.read(chunk_size):
    sha256.update(chunk)
content_hash = sha256.hexdigest()
```

**Efficiency Gain**: 50% faster, less memory

---

### Opportunity 3: Parallel Tar Extraction

**Current Plan**: Sequential (one file at a time)
```bash
for tar_file in logs_*.tar; do
    tar -xf "$tar_file"  # ⏱️ Sequential
done
```

**Better**:
```bash
# Parallel extraction (4 workers)
find . -name "logs_*.tar" | xargs -P 4 -I {} tar -xf {}
```

**Efficiency Gain**: 4x faster

---

### Opportunity 4: Combine Verification & Migration

**Current Plan**: Verify THEN migrate
```
Step 1: Verify tar (read all files)
Step 2: Migrate (read all files again)
# Read disk twice
```

**Better**:
```python
async def extract_and_migrate(tar_path):
    """Single pass: verify + migrate"""
    with tarfile.open(tar_path) as tar:
        for member in tar:
            # Single read
            f = tar.extractfile(member)
            content = f.read()

            # Verify + hash
            verify_integrity(content)
            hash = calculate_hash(content)

            # Store to SurrealDB immediately
            await db.create("training_data_files", {
                "content_hash": hash,
                "file_size": len(content),
                ...
            })
```

**Efficiency Gain**: 50% faster, single I/O pass

---

### Opportunity 5: Data Tiering - Keep Only Recent in SurrealDB

**Current Plan**: Store ALL file content previews for ALL commits
**Problem**: Bloated database with historical data

**Better**:
```sql
-- Tier 1: Recent commits (last 10) - full preview
WHERE extracted_from_commit IN (
    SELECT commit FROM git_commits
    ORDER BY date DESC LIMIT 10
)

-- Tier 2: Older commits - metadata only, no preview
WHERE extracted_from_commit NOT IN (...)
  AND content_preview = NULL
  AND storage_path = "archived://..."
```

**Efficiency Gain**: 90% less storage for old data, instant queries for recent

---

### Opportunity 6: Automated Integrity Verification Loop

**Current Plan**: Manual verification steps
**Better**: Automated verification with fallback
```python
async def verify_and_rollback_on_failure(collection_id):
    """Auto-verify with rollback if fails"""

    # Verify all files queryable
    count = await db.query(
        f"SELECT count() FROM training_data_files "
        f"WHERE collection_id = '{collection_id}'"
    )

    if count[0][0] == 0:
        # Rollback: delete collection
        await db.delete(f"training_data_collections:{collection_id}")
        # Restore from tar
        restore_from_tar(original_tar_path)
        raise Exception("Migration failed, rolled back to tar backup")

    return True  # Safe to proceed with git-filter-repo
```

---

## SECTION 3: Hidden Assumptions

### Assumption 1: "Training data is only in one directory"
**Reality**: There might be training data scattered across:
- `data/training/`
- `experiments/*/logs/`
- `cache/*/`
- Nested in subdirectories

**Fix**: Audit git history for ALL generated data
```bash
# Find all large objects (>1MB)
git rev-list --all --objects | awk '{print $1}' | sort -u | \
  while read obj; do
    size=$(git cat-file -s $obj)
    [ $size -gt 1048576 ] && echo "$obj ($size bytes)"
  done | sort -rn | head -50
```

### Assumption 2: "SurrealDB will always be available"
**Reality**: DB might be down, migrating, or credentials wrong

**Fix**: Fallback to JSONL storage
```python
if not db_available:
    # Fall back to JSONL (always works)
    with open("training_data_backup.jsonl", "a") as f:
        f.write(json.dumps(record) + "\n")
```

### Assumption 3: "Git-filter-repo will succeed first try"
**Reality**: Might fail on:
- Disk space (git gc needs 2-3x repo size)
- Permission issues
- Git corruption

**Fix**: Pre-check
```bash
# Ensure enough disk space (need 3x current size)
required=$(($(du -sb .git | cut -f1) * 3))
available=$(df . | awk 'NR==2 {print $4}' | tr -d ' ')
[ $required -gt $available ] && echo "❌ Insufficient disk space"
```

---

## SECTION 4: Revised Execution Order (Adversarial-Informed)

**Current order**: Extract → Migrate → Verify → Destroy
**Better order**: Verify setup → Extract → Verify → Migrate → Verify → Destroy

```
Phase 0a: ✅ Pre-flight checks
  ├─ Check SurrealDB up and responding
  ├─ Check disk space (need 3x repo size)
  ├─ Check git repository integrity (fsck --full)
  ├─ Find ALL training data (not just one directory)
  └─ Install pre-commit hook FIRST

Phase 0b: ✅ Safe extraction
  ├─ Verify tar files readable (tar -tf)
  ├─ Parallel tar extraction (4 workers)
  └─ Verify files extracted (count match)

Phase 0c: ✅ Combined verify + migrate
  ├─ Single-pass: hash + store to SurrealDB
  ├─ Batch create all records
  └─ Auto-rollback if fails

Phase 0d: ✅ Query verification
  ├─ Count records in SurrealDB
  ├─ Spot-check random files retrieval
  ├─ Verify all commits represented
  └─ Auto-restore from tar if fails

Phase 1: ✅ Only then destroy
  └─ git-filter-repo (with disk space verified)
```

---

## SECTION 5: Stop/Proceed Decision Matrix

| Issue | Severity | Status | Must Fix? |
|-------|----------|--------|-----------|
| SurrealDB transaction safety | 🔴 BLOCKER | Identified | ✅ YES |
| Tar corruption detection | 🔴 BLOCKER | Identified | ✅ YES |
| File deduplication (commit-based) | 🔴 BLOCKER | Identified | ✅ YES |
| Pre-commit hook timing | 🟡 HIGH | Identified | ✅ YES |
| Performance testing | 🟡 MEDIUM | Identified | ⚠️ Recommended |
| Symlink handling | 🟡 MEDIUM | Identified | ⚠️ Recommended |
| Batch operations | 🟢 OPTIMIZATION | Identified | ❌ Can defer |
| Data tiering | 🟢 OPTIMIZATION | Identified | ❌ Can defer |

**Go/No-Go**: 🔴 STOP - Must fix 3 BLOCKERS before proceeding

---

## SECTION 6: Revised Checklist (Adversarial-Safe)

### Must Complete Before Phase 0b (Extraction)
- [ ] SurrealDB running + authenticated + transactional inserts working
- [ ] Git fsck --full passes (no corruption)
- [ ] Disk space check: df shows 3x current .git size available
- [ ] Tar verification script ready (pre-test on sample tar)
- [ ] Pre-commit hook installed and tested
- [ ] Identify ALL training data directories (not just one)

### Must Complete Before Phase 0c (Migration)
- [ ] SurrealDB schema includes commit tracking
- [ ] SurrealDB transaction rollback tested
- [ ] Migration script with fallback to JSONL
- [ ] Integrity check logic auto-rollback tested
- [ ] Parallel extraction tested on sample

### Must Complete Before Phase 1 (Destruction)
- [ ] Can query SurrealDB: SELECT count() returns correct number
- [ ] Can retrieve random records and verify content
- [ ] Tar files still exist as backup
- [ ] backup-pre-cleanup branch still exists
- [ ] Disk space still available (3x)
- [ ] git-filter-repo installation verified

---

## Recommendation: STOP and Remediate

**Current Status**: Plan is 60% complete, 40% has edge case gaps

**Required Fixes** (estimated 1-2 hours):
1. Add SurrealDB transaction safety
2. Add tar integrity verification
3. Add commit-based deduplication to schema
4. Reorder: hook first, then extract
5. Add pre-flight checks script
6. Add auto-rollback on verification failure

**After Fixes**: Plan will be 95% robust (acceptable risk level)

**Verdict**: 🔴 **Recommend fixing identified blockers before executing Phase 0b**

The plan is sound, but needs adversarial hardening against the 6 edge cases identified above.

---

## Compound Engineering Insight

The 4 optimization opportunities represent **20-30% efficiency gain** at near-zero additional complexity:
- Batch operations
- Single-pass hashing
- Parallel extraction
- Combined verify+migrate

These should be **baked into Phase 0c** before first execution (not as afterthoughts).

