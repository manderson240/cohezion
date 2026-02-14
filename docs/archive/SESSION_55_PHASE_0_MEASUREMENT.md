# Session 55: Phase 0 - Universe Artifact Measurement (EXECUTE NOW)

**Goal**: Understand what we're preserving before building infrastructure

**Duration**: 30-45 minutes

**Output**: Detailed metrics on artifacts, patterns, and timeline

---

## Step 0a: Catalog Artifacts

### Command 1: Count files

```bash
cd ~/dev/cohezion

# How many files exist?
git ls-tree -r --name-only HEAD:src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | \
  wc -l
```

**Expected output**: ~100-500 files
**What this tells us**: Scale of universe simulation data

### Command 2: Analyze naming patterns

```bash
# What do the filenames reveal about training?
git ls-tree -r --name-only HEAD:src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | \
  sed 's/_[0-9]*\.txt$//' | \
  sort | \
  uniq -c | \
  sort -rn
```

**Expected output**:
```
  50 lang_1768630692
  30 lang_1768630693
  ...
```
**What this tells us**: Training run IDs (timestamps) showing when universe evolved

### Command 3: Total size

```bash
# How much data is the universe's evolutionary record?
git ls-tree -r --format='%(size)' HEAD:src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | \
  awk '{sum+=$1} END {printf "%.2f MB\n", sum/(1024*1024)}'
```

**Expected output**: ~97 MB
**What this tells us**: Scale of persistence needed in SurrealDB

### Command 4: Historical commits

```bash
# How long has the universe been evolving?
git log --all --follow --oneline -- \
  src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | \
  wc -l
```

**Expected output**: 10-50 commits
**What this tells us**: How many distinct universe evolution phases exist

### Command 5: Size progression (universe evolution timeline)

```bash
# Show size at each major commit (universe got bigger as it evolved?)
git log --all --follow --oneline -- \
  src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | \
  head -10 | \
  cut -d' ' -f1 | \
  while read commit; do
    size=$(git ls-tree -r --format='%(size)' "$commit":src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs 2>/dev/null | \
      awk '{sum+=$1} END {printf "%.1f", sum/(1024*1024)}')
    echo "$commit: ${size} MB"
  done
```

**Expected output**:
```
abc1234: 5.2 MB
abc1235: 7.5 MB
abc1236: 12.3 MB
...
HEAD: 97.2 MB
```
**What this tells us**: Universe grew larger over time (more complex language model)

---

## Step 0b: Extract and Document Metrics

### Create metrics capture script

```bash
#!/bin/bash
# capture_artifact_metrics.sh

cd ~/dev/cohezion

mkdir -p /tmp/cohezion_metrics

echo "=== UNIVERSE ARTIFACT MEASUREMENT ===" > /tmp/cohezion_metrics/summary.txt
echo "Captured at: $(date)" >> /tmp/cohezion_metrics/summary.txt
echo "" >> /tmp/cohezion_metrics/summary.txt

echo "1. FILE COUNT:" >> /tmp/cohezion_metrics/summary.txt
git ls-tree -r --name-only HEAD:src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | \
  wc -l >> /tmp/cohezion_metrics/summary.txt

echo "" >> /tmp/cohezion_metrics/summary.txt
echo "2. TOTAL SIZE:" >> /tmp/cohezion_metrics/summary.txt
git ls-tree -r --format='%(size)' HEAD:src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | \
  awk '{sum+=$1} END {printf "%.2f MB\n", sum/(1024*1024)}' >> /tmp/cohezion_metrics/summary.txt

echo "" >> /tmp/cohezion_metrics/summary.txt
echo "3. TRAINING RUN IDS:" >> /tmp/cohezion_metrics/summary.txt
git ls-tree -r --name-only HEAD:src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | \
  sed 's/_[0-9]*\.txt$//' | \
  sort | \
  uniq -c | \
  sort -rn >> /tmp/cohezion_metrics/summary.txt

echo "" >> /tmp/cohezion_metrics/summary.txt
echo "4. HISTORICAL COMMITS:" >> /tmp/cohezion_metrics/summary.txt
git log --all --follow --oneline -- \
  src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | \
  wc -l >> /tmp/cohezion_metrics/summary.txt

echo "" >> /tmp/cohezion_metrics/summary.txt
echo "5. COMMITS WITH SIZE:" >> /tmp/cohezion_metrics/summary.txt
git log --all --follow --oneline -- \
  src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs | \
  head -20 | \
  cut -d' ' -f1 | \
  while read commit; do
    size=$(git ls-tree -r --format='%(size)' "$commit":src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs 2>/dev/null | \
      awk '{sum+=$1} END {printf "%.1f", sum/(1024*1024)}')
    echo "$commit: ${size} MB"
  done >> /tmp/cohezion_metrics/summary.txt

echo "" >> /tmp/cohezion_metrics/summary.txt
echo "Metrics captured to: /tmp/cohezion_metrics/summary.txt"
cat /tmp/cohezion_metrics/summary.txt
```

### Run measurement

```bash
chmod +x capture_artifact_metrics.sh
./capture_artifact_metrics.sh
```

---

## Step 0c: Document Findings

### Analysis template

Create `/tmp/cohezion_metrics/analysis.md`:

```markdown
# Universe Artifact Measurement Results (Phase 0)

## Key Metrics

**Total Files**: [INSERT COUNT]
**Total Size**: [INSERT SIZE]
**Number of Training Runs**: [INSERT COUNT]
**Number of Commits**: [INSERT COUNT]

## Training Run Timeline

[INSERT COMMITS WITH SIZES]

## Insights

### Universe Evolution Pattern
- Did the universe grow gradually or in leaps?
- Which runs are largest/smallest?
- Are there natural "eras" in the evolution?

### Training Trajectory
- How did language model complexity evolve?
- Are naming patterns consistent across runs?
- Can we infer what hyperparameters changed?

### Data Preservation Importance
- This data represents X months/years of simulation
- File count: X suggests X distinct training snapshots
- Size growth: suggests increasing model/universe complexity

## Next Phase (Phase 1)

- Extract language patterns from samples
- Identify key transitions
- Document which runs represent major universe shifts
- Plan SurrealDB schema based on these patterns
```

---

## Step 0d: Verify Backup Exists

```bash
# Confirm we have safe copies before any changes
cd ~/dev/cohezion

# Check backup branch
git show-ref | grep backup-pre-cleanup
# Expected: refs/heads/backup-pre-cleanup

# Check backup is recent
git log --oneline backup-pre-cleanup -1

# Verify backup is accessible
git rev-parse backup-pre-cleanup^{commit}
# Expected: commit hash (no error)
```

**Success criteria**:
✅ backup-pre-cleanup branch exists
✅ Points to current state
✅ Can be checked out

---

## Phase 0 Completion Checklist

- [ ] Command 1: File count obtained
- [ ] Command 2: Naming patterns analyzed
- [ ] Command 3: Total size measured
- [ ] Command 4: Historical commits counted
- [ ] Command 5: Size progression captured
- [ ] Metrics script created and executed
- [ ] Findings documented in analysis.md
- [ ] Backup branch verified

---

## Expected Output Example

```
=== UNIVERSE ARTIFACT MEASUREMENT ===
Captured at: 2026-02-11 14:30:00

1. FILE COUNT:
   247

2. TOTAL SIZE:
   97.21 MB

3. TRAINING RUN IDS:
   50 lang_1768630692
   45 lang_1768630693
   40 lang_1768630694
   ...

4. HISTORICAL COMMITS:
   23

5. COMMITS WITH SIZE:
   a1b2c3d: 5.2 MB
   b2c3d4e: 7.8 MB
   c3d4e5f: 12.5 MB
   ...
   HEAD: 97.2 MB
```

---

## What This Phase Teaches Us

**Why do measurement first?**

1. **Understand the data**: Know what we're preserving
2. **Extract patterns**: Infer universe evolution trajectory
3. **Plan infrastructure**: Size SurrealDB schema appropriately
4. **Justify cost**: Show why preservation matters
5. **Verify completeness**: Ensure no artifacts are missed

---

## Next: Phase 1 (Pattern Extraction)

After Phase 0 metrics captured, Phase 1 will:
- Analyze semantic content from sample files
- Identify language drift patterns
- Document which universe evolution phases matter most
- Plan focused SurrealDB schema

---

## Execute Now

```bash
chmod +x capture_artifact_metrics.sh
./capture_artifact_metrics.sh
cat /tmp/cohezion_metrics/summary.txt
```

Once output is captured, proceed to Phase 1: Pattern Extraction.

🚀 **Phase 0 is the foundation for all following work.**
