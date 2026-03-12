---
name: batch-backlinks
description: |
  Efficiently add bidirectional backlinks to many vault notes at once. Two patterns:
  (1) Hub-to-corpus: when a batch of related notes was created (cosmology series, APEC
  series, etc.) and existing hub notes don't link back. Adds "Cross-Validation" subsections.
  (2) Cluster cross-linking: when N notes in a research cluster don't link to each other.
  Adds "Other X Presentations/Experiments/Papers" sections to fully connect the cluster.
  Use when: batch of related notes exists with few intra-cluster or hub backlinks.
author: Claude Code
version: 1.1.0
---

# Batch Backlink Injection

## Problem

When a new research corpus of 10+ related notes is created (e.g., 15 indigenous cosmology notes + synthesis), existing vault notes don't link back to them. Adding one link at a time to 20+ existing notes is slow. This skill adds quality backlinks in bulk using a consistent "Cross-Validation" subsection pattern.

## Strategy

Instead of adding individual `[[link]]` entries to Related Concepts sections (fragile, easy to miss), inject a named subsection that:
1. Explains the relationship context
2. Links to the synthesis/index note
3. Provides 2-3 annotated representative links
4. Is visually distinct (named subsection, not buried in a list)

## Step 1: Map the Connection Graph

Before editing anything, understand WHICH existing notes link to WHICH corpus notes:

```bash
# Find all outbound links from the new corpus
grep -oh '\[\[[^]]*\]\]' cortex/new-note-*.md cortex/synthesis-note.md 2>/dev/null | \
  sed 's/\[\[//;s/\]\]//' | sort -u

# For each target, check if it already has backlinks
for target in target-note-1 target-note-2; do
  count=$(grep -c "corpus-note\|synthesis-note" "cortex/$target.md" 2>/dev/null)
  echo "$target: $count backlinks"
done

# Which corpus notes reference which targets
for target in target-note-1 target-note-2; do
  echo "=== $target referenced by ==="
  grep -l "\[\[$target\]\]" cortex/corpus-note-*.md 2>/dev/null | \
    sed 's|cortex/||;s|\.md||' | tr '\n' ', '
  echo ""
done
```

## Step 2: Categorize by Connection Strength

| Category | Corpus refs | Backlink approach |
|----------|-------------|-------------------|
| Heavy (all/most traditions) | 10+ | Full Cross-Validation subsection with 3-4 links |
| Medium (several) | 5-9 | Subsection with 2-3 links |
| Light (1-4) | 1-4 | Subsection with synthesis + 1 representative link |
| Conceptual only (none direct) | 0 | Synthesis link only with annotation |

## Step 3: Inject the Subsection

Find the natural injection point — just before the "Relevance to Cohezion" section or at the end of the Related Concepts section:

```markdown
### [Corpus Name] Cross-Validation

- [[synthesis-note]] — brief description of what the synthesis shows
- [[specific-note-1]] — most relevant specific example with annotation
- [[specific-note-2]] — second example
- [[specific-note-3]] — third example (only for heavy connections)
```

**Key principles:**
- The synthesis note ALWAYS appears first
- Each link has a **specific, non-generic** annotation (not "related" — what specifically?)
- 2-3 tradition notes max (don't list all 15 — that's noise)
- Pick the traditions with the MOST DIRECT structural correspondence to this concept

## Step 4: Read Before Edit

The Edit tool requires reading the file first. To read efficiently, just read the first 10 lines (to confirm it's the right file — already read during tail checks):

```bash
# Read tails to understand where to inject
for f in cortex/target-1.md cortex/target-2.md; do
  echo "=== TAIL: $f ==="; tail -20 "$f"; echo ""
done
```

Then edit with the exact anchor text (the "Relevance to Cohezion" line is usually unique):

```python
Edit(
  file_path="cortex/target-note.md",
  old_string="## Relevance to Cohezion\n\n[first line of section]",
  new_string="### [Corpus] Cross-Validation\n\n[links]\n\n## Relevance to Cohezion\n\n[first line]"
)
```

## Step 5: Batch in Parallel

Read multiple files in one message, then edit multiple files in the next:

```
Message 1: Read file_1 (limit=10), Read file_2 (limit=10), Read file_3 (limit=10)
Message 2: Edit file_1, Edit file_2, Edit file_3, Edit file_4
Message 3: Edit file_5, Edit file_6, Edit file_7, Edit file_8
```

Parallelizing reads saves ~50% time on 20-note batches.

## Step 6: Verify

```bash
# Count backlinks in all target notes
for target in target-1 target-2 target-3; do
  count=$(grep -c "synthesis-note\|corpus-note" "cortex/$target.md" 2>/dev/null)
  echo "$target: $count backlinks"
done

# Confirm pre-existing backlinks still intact (don't want to have broken them)
for target in already-linked-1 already-linked-2; do
  count=$(grep -c "backlink-pattern" "cortex/$target.md" 2>/dev/null)
  echo "$target: $count (should be > 0)"
done
```

## Example: Indigenous Cosmology Corpus

**Corpus**: 15 tradition notes + 1 synthesis = 16 notes
**Existing notes needing backlinks**: 23 notes (20 with 0 backlinks, 3 already done)
**New wiki-links added**: ~63
**Pattern used**:

```markdown
### Indigenous Cosmology Cross-Validation

- [[indigenous-cosmologies-toe-synthesis]] — 15 traditions independently describe [concept] as [specific mapping]
- [[tradition-cosmology-and-toe]] — [tradition's specific contribution]
- [[tradition-cosmology-and-toe]] — [second tradition's contribution]
```

**Heavy connection example** (exotic-vacuum-objects — referenced by all 15 traditions):
```markdown
- [[indigenous-cosmologies-toe-synthesis]] — all 15 traditions independently describe EVO-like phenomena
- [[inuit-cosmology-and-toe]] — Sila as the ZPF's own intelligence; angakkuq trance as EVO formation
- [[yoruba-ifa-cosmology-and-toe]] — Àṣẹ as directed coherent energy identical to EVO charge clustering
- [[dine-navajo-cosmology-and-toe]] — sand paintings as quantum measurement diagrams
```

**Light connection example** (topological-defects — referenced by 1 tradition):
```markdown
- [[indigenous-cosmologies-toe-synthesis]] — multiple traditions describe topological features
- [[hopi-cosmology-and-toe]] — sipapuni as a topological defect connecting worlds
```

## Notes

- Don't add ALL 15 tradition links to every note — that's noise. 2-3 is the sweet spot.
- Pick the traditions with the strongest STRUCTURAL correspondence, not just thematic similarity
- The subsection name should match the corpus ("Indigenous Cosmology", not "Related Traditions")
- If a note already has backlinks in a different format, preserve them — don't replace, add alongside

---

## Pattern 2: Cluster Cross-Linking (Fully Connected Subgraph)

Use when: N notes in a research cluster don't link to each other (e.g., 6 APEC presentations, 5 experiments in a series, 4 papers on a topic).

**Key insight:** Adding an "Other X" section to every note in a cluster creates a fully-connected subgraph with O(n²) link relationships from O(n) edits — the most link-density-efficient operation available.

### Detection

```python
# Find intra-cluster missing links (notes sharing 2+ tags that don't cross-link)
python3 -c "
import os, re

# [build notes dict with tags and links as in vault-health skill]
# Then:
cluster_tag = 'apec'  # or 'evo', 'cs249r', 'mfmp', etc.
cluster = [n for n in notes if cluster_tag in notes[n]['tags']]
for i, n1 in enumerate(cluster):
    for n2 in cluster[i+1:]:
        if n2 not in notes[n1]['links'] and n1 not in notes[n2]['links']:
            print(f'{n1} <-> {n2}')
"
```

### Implementation

For each note in the cluster, append a named section listing all OTHER notes in the cluster:

```markdown
## Other APEC Presentations

- [[apec-note-2]] — [presenter, topic, date]
- [[apec-note-3]] — [presenter, topic, date]
- [[apec-note-4]] — [presenter, topic, date]
```

**Section naming conventions:**
- Research papers from a series → "Other [Topic] Papers"
- Experiment series → "Related Experiments"
- Presentations from an event → "Other [Event] Presentations"
- Notes in a methodology → "Related [Method] Notes"

### Scaling

| Cluster size | Links created | Edits needed | Strategy |
|--------------|---------------|--------------|----------|
| 3-5 notes | 6-10 links | 3-5 edits | Single batch |
| 6-10 notes | 15-45 links | 6-10 edits | Two batches (read all, edit all) |
| 10+ notes | 45+ links | 10+ edits | Three batches; consider synthesizing into an index note first |

### Example: APEC Research Cluster (6 notes → 30 new links)

```
apec-decoding-evos-greenyer.md     +5 links to others
apec-evos-transmutation-anomalies.md  +5 links to others
apec-evos-propulsion-engineering.md   +5 links to others
apec-zero-bias-diodes-zpe.md       +5 links to others
apec-gem-effect-brandenburg.md     +5 links to others
apec-biefeld-brown-electrogravitics.md +5 links to others
──────────────────────────────────────────────────────
Total: 30 new wiki-links, 6 edits, ~5 minutes
```

Each note's section excludes itself and lists the others with brief annotations (presenter, topic, date).

### When to Use Cluster vs Hub Pattern

| Situation | Pattern |
|-----------|---------|
| New corpus, existing hubs don't link back | Hub-to-corpus (Pattern 1) |
| Existing cluster, notes don't link to each other | Cluster cross-linking (Pattern 2) |
| Both: new corpus AND cluster has no internal links | Pattern 1 first, then Pattern 2 |
