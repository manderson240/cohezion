# Session 55: Comprehensive Remediation Plan

**Objective**: Remove training data from git, establish proper data governance, store in SurrealDB
**Status**: Planning phase (learnings extracted, ready to execute)
**Expected Duration**: 1.5-2 hours
**Token Budget**: 1,000-1,500

---

## Phase 1: Immediate Fix - Remove from Git History

### Step 1a: Remove training data directory
```bash
cd ~/dev/cohezion
git filter-repo --invert-paths \
  --path "src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs" \
  --force
```

**What this does**:
- Removes all commits containing training data files
- Rewrites git history (safe because we have backups)
- Reduces repository from ~13GB to ~6-7GB
- Unblocks GitHub push

**Expected result**: Repository size drops 50%+

### Step 1b: Add .gitignore entries (prevent recurrence)
```gitignore
# === NEVER COMMIT GENERATED DATA ===
# Training data
**/logs/
**/*.log
**/output/
**/results/
**/experiments/
/data/training/
/data/cache/

# Model outputs (use git-lfs instead)
*.pkl
*.pt
*.pth
*.h5
*.onnx

# Ephemeral artifacts
/tmp/
__pycache__/
*.pyc
.cache/
```

### Step 1c: Verify cleanup
```bash
git fsck --full
du -sh .git/
git rev-list --all --objects --disk-usage | head -20
```

---

## Phase 2: GitHub Deployment (Post-Cleanup)

### Step 2a: Push to GitHub
```bash
git push git@github.com:manderson240/cohezion.git \
  session-55-test-fixes-main --force-with-lease --verbose
```

Expected: Success (size now ~6-7GB, within limits, no 97MB tree objects)

### Step 2b: Validation
```bash
# Verify on GitHub
git ls-remote git@github.com:manderson240/cohezion.git \
  session-55-test-fixes-main

# Verify no large objects
git rev-list --all --objects --disk-usage | \
  awk '{if ($1 > 10485760) print}' | wc -l
# Expected: 0 (no objects >10MB)
```

---

## Phase 3: Git-LFS Setup (For Future Models)

### Step 3a: Install git-lfs
```bash
# Ubuntu/Debian
sudo apt-get install git-lfs

# macOS
brew install git-lfs

# Verify
git lfs --version
```

### Step 3b: Configure .gitattributes
```
# Track model files with git-lfs
*.pt filter=lfs diff=lfs merge=lfs -text
*.pth filter=lfs diff=lfs merge=lfs -text
*.h5 filter=lfs diff=lfs merge=lfs -text
*.pkl filter=lfs diff=lfs merge=lfs -text
*.onnx filter=lfs diff=lfs merge=lfs -text

# Large checkpoints
data/flume/checkpoints/*.pt filter=lfs diff=lfs merge=lfs -text
data/rl/checkpoints/*.pt filter=lfs diff=lfs merge=lfs -text
```

### Step 3c: Initialize git-lfs
```bash
git lfs install
git add .gitattributes
git commit -m "chore: Add git-lfs configuration for model files"
git push origin session-55-test-fixes-main
```

**Why git-lfs**:
- Models are large (100MB+) but infrequently changed
- Git-lfs stores pointer files in git, actual models in separate storage
- Keeps git responsive while preserving model versioning
- GitHub includes free LFS storage (1GB per repository)

---

## Phase 4: SurrealDB Schema for Training Data

### Step 4a: Define training data schema
```sql
-- Training data metadata table
DEFINE TABLE training_data SCHEMAFULL
  PERMISSIONS FOR select, create, update, delete WHERE owner = $auth.id;

DEFINE FIELD uid ON training_data TYPE string;
DEFINE FIELD owner ON training_data TYPE string;
DEFINE FIELD dataset_name ON training_data TYPE string;
DEFINE FIELD dataset_type ON training_data TYPE enum<language_model, rl_training, simulation>;
DEFINE FIELD created_at ON training_data TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON training_data TYPE datetime DEFAULT time::now();
DEFINE FIELD version ON training_data TYPE string;
DEFINE FIELD description ON training_data TYPE string;
DEFINE FIELD tags ON training_data TYPE array;
DEFINE FIELD metadata ON training_data TYPE object;
DEFINE FIELD size_bytes ON training_data TYPE int;
DEFINE FIELD storage_path ON training_data TYPE string;  -- S3, GCS, etc.
DEFINE FIELD checksum ON training_data TYPE string;  -- For integrity
DEFINE FIELD status ON training_data TYPE enum<draft, ready, archived>;

-- Training runs/experiments table
DEFINE TABLE training_runs SCHEMAFULL;

DEFINE FIELD uid ON training_runs TYPE string;
DEFINE FIELD training_data->uid ON training_runs TYPE record;
DEFINE FIELD model_type ON training_runs TYPE string;
DEFINE FIELD hyperparameters ON training_runs TYPE object;
DEFINE FIELD started_at ON training_runs TYPE datetime;
DEFINE FIELD completed_at ON training_runs TYPE datetime;
DEFINE FIELD metrics ON training_runs TYPE object;
DEFINE FIELD artifacts_path ON training_runs TYPE string;
DEFINE FIELD status ON training_runs TYPE enum<pending, running, completed, failed>;

-- Relationships
DEFINE RELATION generated_by ON training_data TYPE training_runs;
DEFINE RELATION used_in ON training_runs TYPE training_data;
```

### Step 4b: Create indexes for query performance
```sql
DEFINE INDEX training_data_by_name ON training_data(dataset_name);
DEFINE INDEX training_data_by_type ON training_data(dataset_type);
DEFINE INDEX training_data_by_created ON training_data(created_at);
DEFINE INDEX training_runs_by_status ON training_runs(status);
DEFINE INDEX training_runs_by_model ON training_runs(model_type);
```

### Step 4c: Create access functions
```python
# src/cohezion/knowledge_graph/training_data_store.py

from cohezion.core.persistence import get_surreal_client
import hashlib
from pathlib import Path


class TrainingDataStore:
    """Store training data metadata in SurrealDB"""

    def __init__(self):
        self.db = get_surreal_client()

    async def record_training_data(
        self,
        dataset_name: str,
        dataset_type: str,
        storage_path: str,
        description: str = None,
        tags: list = None,
        metadata: dict = None,
    ) -> dict:
        """Record training data in SurrealDB"""

        # Calculate checksum for integrity
        checksum = self._calculate_checksum(storage_path)
        size_bytes = Path(storage_path).stat().st_size

        record = {
            "dataset_name": dataset_name,
            "dataset_type": dataset_type,
            "storage_path": storage_path,
            "description": description or "",
            "tags": tags or [],
            "metadata": metadata or {},
            "checksum": checksum,
            "size_bytes": size_bytes,
            "status": "ready",
        }

        result = await self.db.create("training_data", [record])
        return result[0]

    async def record_training_run(
        self, training_data_id: str, model_type: str, hyperparameters: dict, artifacts_path: str
    ) -> dict:
        """Record training run in SurrealDB"""

        record = {
            "training_data": f"training_data:{training_data_id}",
            "model_type": model_type,
            "hyperparameters": hyperparameters,
            "artifacts_path": artifacts_path,
            "status": "pending",
        }

        result = await self.db.create("training_runs", [record])
        return result[0]

    async def list_training_data(
        self, dataset_type: str = None, tags: list = None, limit: int = 100
    ) -> list:
        """Query training data by type/tags"""

        query = "SELECT * FROM training_data WHERE status = 'ready'"

        if dataset_type:
            query += f" AND dataset_type = '{dataset_type}'"

        if tags:
            query += f" AND array::some(tags, {tags})"

        query += f" ORDER BY created_at DESC LIMIT {limit}"

        results = await self.db.query(query)
        return results

    @staticmethod
    def _calculate_checksum(file_path: str) -> str:
        """Calculate SHA256 checksum for file"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
```

### Step 4d: Update training pipeline
```python
# Example: Update existing training code to use SurrealDB

from cohezion.knowledge_graph.training_data_store import TrainingDataStore


async def train_model(config):
    """Training pipeline that records data in SurrealDB"""

    store = TrainingDataStore()

    # Record the training data
    training_data = await store.record_training_data(
        dataset_name=config.dataset_name,
        dataset_type="language_model",
        storage_path="/external/training/lang_data.pkl",  # External storage
        description=f"Language model training data - {config.version}",
        tags=["language-model", "universe-simulation", config.version],
        metadata={"vocab_size": 50000, "sequence_length": 2048, "preprocessing": "standard"},
    )

    # Record the training run
    training_run = await store.record_training_run(
        training_data_id=training_data["uid"],
        model_type="transformer",
        hyperparameters=config.model_params,
        artifacts_path="/external/models/lang_model_v1.pt",  # git-lfs or external
    )

    # Training happens here...
    model = train_transformer(config)

    # Update run status
    await store.db.update(
        f"training_runs:{training_run['uid']}", {"status": "completed", "metrics": model.metrics}
    )

    return model
```

---

## Phase 5: Data Governance Documentation

### Step 5a: Update CLAUDE.md
Add section: "Data Storage Architecture"
```markdown
## Data Storage Architecture

### Three-Tier Storage Strategy

1. **Version Control (Git)**
   - Source code (Python, configs, documentation)
   - Small reference data (<1MB files)
   - NOT: Generated data, models, training artifacts

2. **Git-LFS (Large File Storage)**
   - Model checkpoints (*.pt, *.h5, *.pkl)
   - Trained weights (versioned, infrequently changed)
   - Compressed archives of large data
   - GitHub LFS: 1GB free, can purchase more

3. **External Storage (SurrealDB + Cloud)**
   - Training data metadata → SurrealDB
   - Training data files → S3/GCS (ephemeral)
   - Experiment logs → SurrealDB
   - Simulation outputs → External (not in git)

### What Goes Where

| Data Type | Storage | Reason |
|-----------|---------|--------|
| Source code | Git | Version control needed |
| .gitignore | Git | Prevents future mistakes |
| Model checkpoints | Git-LFS | Infrequently changed, versioning helpful |
| Training data | SurrealDB + S3 | Large, ephemeral, metadata critical |
| Experiment logs | SurrealDB | Metadata searchable, actual logs external |
| Simulation results | External | Large, regenerable, research artifacts |
| Processed datasets | S3/GCS | Large, stable, referenced from SurrealDB |

### Implementation

Pre-commit hook prevents violations:
```bash
# Reject files > 10MB
# Reject common data extensions without git-lfs
# Alert on suspicious commits
```

SurrealDB stores all metadata:
- What training data exists
- Where it's stored (S3 path, etc.)
- When it was created
- What models used it
- Integrity checksums
```
```

### Step 5b: Create pre-commit hook
```bash
#!/bin/bash
# .git/hooks/pre-commit

set -e

# Reject large files
for file in $(git diff --cached --name-only); do
  size=$(git cat-file -s ":$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null || echo 0)
  if [ "$size" -gt 10485760 ]; then
    echo "❌ File too large (>10MB): $file"
    echo "   Use git-lfs (git lfs track '*.ext') or external storage"
    exit 1
  fi
done

# Reject common data files
for ext in .pkl .pkl.gz .npy .h5 .csv .jsonl .log; do
  git diff --cached --name-only | grep "$ext" | while read file; do
    # Check if tracked by git-lfs
    if ! git ls-files --stage "$file" | grep -q "160000"; then
      echo "❌ Data file without git-lfs: $file"
      echo "   Use: git lfs track '$file'"
      exit 1
    fi
  done
done

echo "✅ Pre-commit checks passed"
```

---

## Phase 6: Execution Checklist

- [ ] **Phase 1**: Remove training data from git history
  - [ ] Run git-filter-repo
  - [ ] Verify size reduction (13GB → 6-7GB)
  - [ ] Test git fsck passes
  - [ ] Add .gitignore entries

- [ ] **Phase 2**: Deploy to GitHub
  - [ ] SSH push to session-55-test-fixes-main
  - [ ] Verify no large objects remain
  - [ ] Run validation suite

- [ ] **Phase 3**: Set up git-lfs
  - [ ] Install git-lfs
  - [ ] Create .gitattributes
  - [ ] Commit LFS configuration
  - [ ] Test with model file

- [ ] **Phase 4**: SurrealDB schema
  - [ ] Create training_data table
  - [ ] Create training_runs table
  - [ ] Define indexes
  - [ ] Implement TrainingDataStore class
  - [ ] Test with sample data

- [ ] **Phase 5**: Documentation
  - [ ] Update CLAUDE.md
  - [ ] Add pre-commit hook
  - [ ] Document git-lfs workflow
  - [ ] Create runbook for adding training data

- [ ] **Phase 6**: Integration
  - [ ] Update training pipeline to use TrainingDataStore
  - [ ] Test end-to-end
  - [ ] Verify SurrealDB queries work
  - [ ] Create migration guide for existing training data

---

## Expected Outcomes

### Immediate (Today)
- ✅ Repository reduced from 13GB → 6-7GB
- ✅ GitHub push succeeds
- ✅ Validation suite passes
- ✅ Entire.io captures journey

### Short-term (This session)
- ✅ git-lfs configured and tested
- ✅ SurrealDB schema ready
- ✅ Pre-commit hook prevents future violations
- ✅ Documentation updated

### Long-term (Foundation)
- ✅ Training data properly governed (SurrealDB)
- ✅ Models versioned (git-lfs)
- ✅ Code clean (no data bloat)
- ✅ Scalable architecture for future growth

---

## Success Metrics

| Metric | Target | Verification |
|--------|--------|--------------|
| Repository size | < 5GB | `du -sh .git/` |
| Large objects | 0 | `git rev-list --objects --disk-usage` |
| GitHub push | Success | SSH push completes |
| git-lfs working | Yes | Track and test .pt file |
| SurrealDB schema | Verified | Query training_data table |
| Pre-commit hook | Active | Attempt commit with large file |

---

## Token Budget

| Phase | Estimate | Actual |
|-------|----------|--------|
| 1: Remove from git | 200 | TBD |
| 2: GitHub deployment | 100 | TBD |
| 3: git-lfs setup | 150 | TBD |
| 4: SurrealDB schema | 300 | TBD |
| 5: Documentation | 200 | TBD |
| 6: Integration | 250 | TBD |
| **Total** | **1,200** | **TBD** |

---

## Ready to Execute?

All phases planned. Backups verified. Learnings extracted. Documentation prepared.

Ready to proceed with Phase 1 (git-filter-repo cleanup)? 🚀

