---
name: research-vault-surrealdb-pipeline
description: |
  Standing workflow for "consider <URL>" research sessions in Cohezion.
  Every research item must produce: (1) vault note at research/YYYY-MM-DD-slug.md,
  (2) SurrealDB record as research_item:id, (3) backlog entry if actionable.
  Use when: user says "consider <URL>", after any research/assessment session,
  or when logging external papers/articles/discoveries.
  Key gotcha: surrealdb_import_concepts fails with asyncio error — use
  surrealdb_query CREATE statements directly instead.
author: Claude Code
version: 1.0.0
---

# Research → Vault + SurrealDB Pipeline

## Problem

User sessions that "consider" URLs or research topics produce ephemeral assessments that vanish after context compaction. Need durable per-item records in both vault (human-readable) and SurrealDB (queryable).

## Standing Instruction

> "Everytime I ask you to research something at least make a vault and surrealdb entry. If it's worth including as part of Cohezion put it in the backlog."

## Workflow

### Step 1: Vault note (one per item)
```
path: research/YYYY-MM-DD-<slug>.md
```

Required frontmatter:
```yaml
---
type: research
date: YYYY-MM-DD
source: <URL or citation>
tags: [relevant, tags]
cohezion_relevance: low|medium|high|very-high
backlog: true|false
---
```

Content: summary, cohezion relevance (with specific component names + file paths), backlog items.

**Batch parallel**: write 4 vault notes at a time in a single message with parallel tool calls.

### Step 2: SurrealDB record (one per item)

**IMPORTANT**: `surrealdb_import_concepts` fails with `asyncio.run() cannot be called from a running event loop`. Use `surrealdb_query` CREATE statements instead, batched in one call:

```sql
CREATE research_item:<slug> SET
  name = "...",
  date = "YYYY-MM-DD",
  source = "...",
  summary = "...",
  tags = ["tag1", "tag2"],
  backlog = true,
  backlog_item = "...",
  vault_path = "research/YYYY-MM-DD-slug.md";
```

Batch all CREATEs in a single `surrealdb_query` call (semicolon-separated).

### Step 3: Consolidated backlog file

```
path: backlog/YYYY-MM-DD-research-derived-backlog.md
```

Organise by priority (HIGH/MEDIUM/LOW). Include vault_path cross-reference for each item. Separate "NOT BACKLOGGED" section for items assessed as not applicable.

## Backlog Decision Criteria

| Include in backlog | Do NOT include |
|---|---|
| Actionable with specific file/component | Not applicable to server-side Cohezion |
| Physics layer enrichment (anchors, gauge theory) | Browser-only features |
| Compound loop improvements | Already implemented |
| New zero-param ARC solver patterns | One-line doc changes (inline instead) |

## Example: Batch SurrealDB query

```sql
CREATE research_item:gargamelle_1973 SET
  name = "Gargamelle — Weak Neutral Current (CERN 1973)",
  date = "2026-06-24",
  source = "home.cern/science/experiments/gargamelle",
  summary = "First evidence of Z boson. Relevant to FourFabricGauge neutral/charged current split, U(1)^4 ObservationalAnchor.",
  tags = ["cern", "gauge-theory", "observational-anchor"],
  backlog = true,
  backlog_item = "Add Gargamelle 1973 ObservationalAnchor for U(1)^4 cosmogony stage",
  vault_path = "research/2026-06-24-gargamelle-weak-neutral-current.md";

CREATE research_item:cross_origin_storage SET
  name = "Cross-Origin Storage API",
  date = "2026-06-24",
  source = "huggingface.co/blog/cross-origin-storage",
  summary = "Browser proposal. NOT applicable — all inference server-side.",
  tags = ["browser", "not-applicable"],
  backlog = false,
  vault_path = "research/2026-06-24-cross-origin-storage-api.md";
```

## Query backlog items later

```sql
SELECT name, backlog_item, vault_path FROM research_item WHERE backlog = true ORDER BY date DESC;
```
