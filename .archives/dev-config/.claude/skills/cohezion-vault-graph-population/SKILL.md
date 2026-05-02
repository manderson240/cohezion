---
name: cohezion-vault-graph-population
description: |
  Populate SurrealDB neurons/synapses from Obsidian vault for Graph HIHO.
  Use when: (1) Graph HIHO is stuck at 0.000 with empty neurons/synapses
  tables, (2) after a fresh SurrealDB install/reset, (3) vault has grown
  significantly and graph hasn't been re-populated, (4) reciprocity is 0.0
  despite wikilinks existing in vault notes.
  Includes: vault scan → neurons, wikilink extraction → synapses, backlink
  creation → reciprocity. Uses SELECT VALUE for subquery joins (L295).
author: Claude Code
version: 1.0.0
---

# Cohezion Vault Graph Population

## Problem

SurrealDB `neurons` and `synapses` tables are empty, causing Graph HIHO = 0.000
despite a rich Obsidian vault existing at `~/vaults/cohezion-vault/`.

Note: `neurons`/`synapses` are the **knowledge graph** domain (vault-keeper),
separate from `prompt_artifacts`/`universe_snapshots` (genesis executor domain).
Populating one does not affect the other (L280).

## Steps

### Step 1: Scan vault → create neurons

Target the knowledge-bearing brain regions (not infra/config dirs):

```python
KNOWLEDGE_DIRS = {
    'cerebellum', 'cortex', 'hippocampus', 'neocortex', 'prefrontal', 'thalamus',
    'decisions', 'experiments', 'patterns', 'learnings', 'LEARNINGS', 'research',
    'competition', 'competition_intelligence', 'daily', 'missions', 'reports',
}
```

For each `.md` file, create a neuron with `path` (relative to vault root), `title`
(stem), `content` (first 500 chars), `tags` (from YAML frontmatter), `cluster_id`
(directory name), `activation=0.5`, `stage="active"`.

**YAML frontmatter extraction:**
```python
if content.startswith('---'):
    end = content.find('---', 3)
    if end > 0:
        fm = yaml.safe_load(content[3:end])
        tags = fm.get('tags', [])
```

### Step 2: Extract wikilinks → create synapses

```python
WIKILINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')
links = WIKILINK_RE.findall(content)
for target_title in links[:20]:  # Cap at 20 per note
    CREATE synapses SET source=$path, target=$title, link_type="wikilink"
```

Note: `source` = full relative path (e.g. `cerebellum/note.md`),
`target` = wikilink title (e.g. `FLUME-First Principle`). These formats differ.

### Step 3: Create backlinks → raise reciprocity

```python
# Build lookup tables
title_to_path = {n['title']: n['path'] for n in neurons}
path_to_title = {n['path']: n['title'] for n in neurons}

for syn in wikilink_synapses:
    reverse_source = title_to_path.get(syn['target'])  # target title → path
    reverse_target = path_to_title.get(syn['source'])  # source path → title
    if reverse_source and reverse_target:
        CREATE synapses SET source=$reverse_source, target=$reverse_target,
            link_type="backlink"
```

~65% of wikilinks resolve (links to notes outside scanned dirs don't).

### Step 4: Verify with SELECT VALUE (L295)

```python
# MUST use SELECT VALUE for IN subqueries in SurrealDB 3.0
connected = await db.query(
    'SELECT count() FROM neurons WHERE '
    'path IN (SELECT VALUE source FROM synapses) OR '
    'title IN (SELECT VALUE target FROM synapses) GROUP ALL'
)
```

## Expected Outcomes

After running on a ~3000-note vault with 16 knowledge dirs:
- ~981 neurons, ~5119 wikilinks, ~3330 backlinks = ~8449 total synapses
- Connectivity: ~0.86 (target >0.8) ✓
- Reciprocity: ~0.65 (target >0.6) ✓
- Freshness: 1.0 (all just created) ✓
- Orphan ratio: ~0.5 (daily/mission notes often disconnected)
- **Graph HIHO: ~0.74** (above target 0.5 ± 0.15) ✓

## Raising Orphan Ratio Further

The ~50% orphan ratio is from daily notes and mission logs without wikilinks.
To improve: add `[[related]]` links to daily notes, or extend scan to include
more dirs (`daily/` notes tend to not cross-reference).

## SurrealDB Connection Pattern

```python
from surrealdb import AsyncSurreal

async with AsyncSurreal('ws://localhost:8001/rpc') as db:
    await db.signin({'username': 'root', 'password': 'root'})
    await db.use('cohezion', 'vault')  # Use vault DB, not genesis DB
```

## References

- Session 96, L295 (SELECT VALUE fix)
- `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` L280 (two persistence graphs)
- `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` L295 (SELECT VALUE)
