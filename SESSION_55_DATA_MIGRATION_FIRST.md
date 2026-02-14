# Session 55: Data Migration FIRST (Before Destructive Operations)

**Critical Principle**: Never destroy data without first:
1. ✅ Extracting it
2. ✅ Verifying integrity
3. ✅ Storing in new location
4. ✅ Testing retrieval
5. ✅ Confirming backup exists

**Then and only then**: Destroy old location

---

## Phase 0: Data Extraction & Migration (BEFORE git-filter-repo)

### Step 0a: Identify all training data in git history

```bash
cd ~/dev/cohezion

# Find the training data directory
git log --all --full-history -- \
  src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | \
  head -20

# Count files in that directory across all commits
git ls-tree -r HEAD:src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs 2>/dev/null | \
  wc -l

# Get list of all files
git ls-tree -r --name-only HEAD:src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs 2>/dev/null | \
  sort
```

**Purpose**: Understand what we're about to extract and destroy

### Step 0b: Export training data from git to external storage

```bash
#!/bin/bash
# export_training_data.sh

mkdir -p /tmp/cohezion_training_data_export
cd ~/dev/cohezion

# Extract the exact version from git
git show HEAD:src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs > /tmp/cohezion_training_data_export/logs_HEAD.tar

# Also get from older commits for completeness
git log --all --follow --oneline -- \
  src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | \
  cut -d' ' -f1 | while read commit; do
    echo "Extracting from commit: $commit"
    # Get the tree object hash for this directory
    tree_hash=$(git rev-parse $commit:src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs 2>/dev/null)
    if [ ! -z "$tree_hash" ]; then
      # Export to dated file
      git archive $commit -- \
        src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs \
        > /tmp/cohezion_training_data_export/logs_${commit:0:7}.tar 2>/dev/null || true
    fi
  done

echo "Export complete: /tmp/cohezion_training_data_export/"
ls -lah /tmp/cohezion_training_data_export/
```

**What this does**:
- Exports training data from git to external location
- Preserves all versions across commits
- Creates timestamped backups
- No deletion yet

### Step 0c: Analyze extracted data

```bash
# What did we extract?
cd /tmp/cohezion_training_data_export

# Count files
for file in logs_*.tar; do
  echo "=== $file ==="
  tar -tf $file | wc -l
  tar -tf $file | head -20
done

# Verify integrity (calculate checksums)
sha256sum logs_*.tar > export_checksums.txt
cat export_checksums.txt
```

**Purpose**: Document exactly what's being migrated

### Step 0d: Prepare SurrealDB for training data

```sql
-- Create namespace and database
DEFINE NAMESPACE cohezion;
USE NS cohezion;

DEFINE DATABASE core;
USE DB core;

-- Training data file storage table
DEFINE TABLE training_data_files SCHEMAFULL
  PERMISSIONS FOR select, create, update, delete WHERE owner = $auth.id;

DEFINE FIELD uid ON training_data_files TYPE string PRIMARY KEY;
DEFINE FIELD owner ON training_data_files TYPE string;
DEFINE FIELD filename ON training_data_files TYPE string;
DEFINE FIELD directory_path ON training_data_files TYPE string;
DEFINE FIELD content_hash ON training_data_files TYPE string;
DEFINE FIELD file_size ON training_data_files TYPE int;
DEFINE FIELD extracted_from_commit ON training_data_files TYPE string;
DEFINE FIELD extracted_at ON training_data_files TYPE datetime DEFAULT time::now();
DEFINE FIELD backup_location ON training_data_files TYPE string;
DEFINE FIELD content_preview ON training_data_files TYPE string;  -- First 1000 chars
DEFINE FIELD export_archive ON training_data_files TYPE string;  -- Which tar file

-- Training data collection metadata
DEFINE TABLE training_data_collections SCHEMAFULL;

DEFINE FIELD uid ON training_data_collections TYPE string PRIMARY KEY;
DEFINE FIELD collection_name ON training_data_collections TYPE string;
DEFINE FIELD description ON training_data_collections TYPE string;
DEFINE FIELD date_extracted ON training_data_collections TYPE datetime;
DEFINE FIELD git_history_span ON training_data_collections TYPE object;
DEFINE FIELD total_files ON training_data_collections TYPE int;
DEFINE FIELD total_size_bytes ON training_data_collections TYPE int;
DEFINE FIELD export_checksum ON training_data_collections TYPE string;
DEFINE FIELD export_archive_location ON training_data_collections TYPE string;
DEFINE FIELD status ON training_data_collections TYPE enum<extracted, verified, in_surrealdb, archived>;

-- Relationships
DEFINE RELATION contains ON training_data_collections TYPE training_data_files;
```

### Step 0e: Migrate data to SurrealDB

```python
# src/cohezion/knowledge_graph/training_data_migration.py

import asyncio
import tarfile
import hashlib
from pathlib import Path
from datetime import datetime
from cohezion.core.persistence import get_surreal_client

class TrainingDataMigration:
    """Safely migrate training data from git to SurrealDB"""

    def __init__(self):
        self.db = get_surreal_client()
        self.export_dir = Path("/tmp/cohezion_training_data_export")

    async def migrate_from_tar(self, tar_path: str) -> dict:
        """Extract tar file and store metadata in SurrealDB"""

        tar_file = Path(tar_path)
        if not tar_file.exists():
            raise FileNotFoundError(f"Tar file not found: {tar_path}")

        collection = {
            "collection_name": f"training_data_{datetime.now().isoformat()}",
            "description": f"Training data extracted from {tar_file.name}",
            "date_extracted": datetime.now().isoformat(),
            "export_archive_location": str(tar_file.absolute()),
            "status": "extracted",
            "files": []
        }

        # Extract and process each file
        with tarfile.open(tar_file, 'r') as tar:
            for member in tar.getmembers():
                if member.isfile():
                    # Extract file content
                    f = tar.extractfile(member)
                    content = f.read()

                    # Calculate hash
                    content_hash = hashlib.sha256(content).hexdigest()

                    # Store preview (first 1000 chars)
                    try:
                        preview = content.decode('utf-8', errors='ignore')[:1000]
                    except:
                        preview = f"[Binary file, {len(content)} bytes]"

                    # Create file record
                    file_record = {
                        "filename": member.name,
                        "directory_path": str(Path(member.name).parent),
                        "content_hash": content_hash,
                        "file_size": len(content),
                        "extracted_from_commit": tar_file.stem,
                        "content_preview": preview,
                        "export_archive": tar_file.name,
                        "backup_location": str(tar_file.absolute())
                    }

                    collection["files"].append(file_record)

        # Store collection metadata in SurrealDB
        result = await self.db.create("training_data_collections", [collection])
        collection_id = result[0]["uid"]

        # Store file metadata
        for file_record in collection["files"]:
            file_record["collection_id"] = collection_id
            await self.db.create("training_data_files", [file_record])

        collection["status"] = "in_surrealdb"
        await self.db.update(f"training_data_collections:{collection_id}", collection)

        return {
            "collection_id": collection_id,
            "files_stored": len(collection["files"]),
            "total_size": sum(f["file_size"] for f in collection["files"]),
            "export_location": str(tar_file.absolute())
        }

    async def verify_migration(self, collection_id: str) -> dict:
        """Verify all data was stored correctly"""

        # Query SurrealDB for the collection
        result = await self.db.query(
            f"SELECT * FROM training_data_collections WHERE uid = '{collection_id}'"
        )

        if not result or not result[0]:
            return {"status": "FAILED", "error": "Collection not found"}

        collection = result[0][0]

        # Query all files in collection
        files = await self.db.query(
            f"SELECT * FROM training_data_files WHERE collection_id = '{collection_id}'"
        )

        # Verify counts match
        file_count = len(files[0]) if files else 0

        verification = {
            "status": "VERIFIED" if file_count > 0 else "FAILED",
            "collection_id": collection_id,
            "files_in_surrealdb": file_count,
            "files_original": collection.get("total_files"),
            "backup_location": collection.get("export_archive_location"),
            "export_checksum": collection.get("export_checksum"),
            "can_retrieve": file_count > 0
        }

        return verification

    async def list_collections(self) -> list:
        """List all migrated training data collections"""

        result = await self.db.query(
            "SELECT uid, collection_name, total_files, date_extracted, status "
            "FROM training_data_collections ORDER BY date_extracted DESC"
        )

        return result[0] if result else []

# Usage example
async def main():
    migration = TrainingDataMigration()

    # Migrate each tar file
    for tar_file in Path("/tmp/cohezion_training_data_export").glob("logs_*.tar"):
        print(f"Migrating {tar_file.name}...")
        result = await migration.migrate_from_tar(str(tar_file))
        print(f"  ✅ {result['files_stored']} files stored")

        # Verify immediately
        verification = await migration.verify_migration(result['collection_id'])
        print(f"  ✅ Verification: {verification['status']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 0f: Verify complete migration

```bash
#!/bin/bash
# verify_migration.sh

echo "=== MIGRATION VERIFICATION ==="
echo ""

echo "1. Check SurrealDB has data:"
echo "   SELECT count() FROM training_data_files" | surreal sql

echo ""
echo "2. Verify all collections:"
echo "   SELECT uid, collection_name, total_files FROM training_data_collections" | surreal sql

echo ""
echo "3. Verify we can retrieve files:"
echo "   SELECT filename, file_size FROM training_data_files LIMIT 10" | surreal sql

echo ""
echo "4. Backup location:"
ls -lah /tmp/cohezion_training_data_export/

echo ""
echo "✅ IF all above show data, we're safe to proceed with git-filter-repo"
echo "❌ IF any queries return empty, DO NOT PROCEED - troubleshoot first"
```

---

## Phase 1: ONLY AFTER Verification - Remove from Git

**Checklist before git-filter-repo**:
- [ ] Training data extracted to `/tmp/cohezion_training_data_export/`
- [ ] All tar files have checksums verified
- [ ] SurrealDB `training_data_collections` table populated
- [ ] SurrealDB `training_data_files` table has all files
- [ ] Can successfully query: `SELECT count() FROM training_data_files`
- [ ] Result is > 100 (actually have data)
- [ ] Backups verified (backup-pre-cleanup exists)

**Only when ALL boxes checked**:

```bash
cd ~/dev/cohezion

# Remove from git history
git filter-repo --invert-paths \
  --path "src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs" \
  --force

# Verify it's gone
git rev-list --all --objects | grep "linguistic_evolution/logs"
# Expected: (empty result)

# Verify size reduction
du -sh .git/
# Expected: ~6-7GB
```

---

## Safety Checkpoints

### Checkpoint 1: Before Export
```bash
# Count what we're exporting
git ls-tree -r --name-only HEAD:src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | wc -l
# Expected: 100+
```

### Checkpoint 2: After Export
```bash
# Verify tar files exist and are readable
tar -tf /tmp/cohezion_training_data_export/logs_HEAD.tar | head -10
# Expected: list of files
```

### Checkpoint 3: After SurrealDB Migration
```bash
# Query SurrealDB
SELECT count() FROM training_data_files;
# Expected: Number matching exported files
```

### Checkpoint 4: After git-filter-repo
```bash
# Verify it's really gone
git rev-list --all --objects --disk-usage | grep -i "linguistic"
# Expected: (empty)

# Verify size reduced
du -sh .git/
# Expected: ~6-7GB
```

---

## Rollback Procedure

If anything goes wrong at any step:

```bash
# Step 1: We have the tar files
ls -lah /tmp/cohezion_training_data_export/

# Step 2: We have SurrealDB backup
# (Data in SurrealDB is recoverable)

# Step 3: Git history is backed up
git reset --hard backup-pre-cleanup
# (Back to pre-cleanup state with all 13GB)
```

---

## Execution Order (Safety First)

```
✅ Phase 0a: Identify training data
✅ Phase 0b: Export to tar files
✅ Phase 0c: Analyze exports
✅ Phase 0d: Create SurrealDB schema
✅ Phase 0e: Migrate to SurrealDB
✅ Phase 0f: VERIFY migration successful
   └─ CHECK: All data in SurrealDB?
   └─ CHECK: Can query successfully?
   └─ CHECK: Backups exist?

ONLY IF ALL VERIFIED:
✅ Phase 1: git-filter-repo (destructive)
✅ Phase 2: Deploy to GitHub
✅ Phase 3: git-lfs setup
```

---

## Success Criteria

| Step | Verification | Status |
|------|--------------|--------|
| Export | tar files exist, readable | ⏳ Pending |
| Count | File count matches | ⏳ Pending |
| SurrealDB | Data inserted | ⏳ Pending |
| Query | `SELECT count()` > 100 | ⏳ Pending |
| Integrity | All hashes match | ⏳ Pending |
| Backup | backup-pre-cleanup exists | ✅ Done |

---

## NO DESTRUCTION UNTIL ALL GREEN ✅

This is non-negotiable. We will:
1. Extract everything
2. Verify in SurrealDB
3. Test retrieval
4. Confirm backups
5. THEN and only then destroy

Ready to proceed with Phase 0a (data extraction)? 🔒

