---
title: "Automated Concept Extraction from Vault Papers"
date: "2026-02-07"
tags: [pattern, automation, knowledge-management, concept-extraction]
aspect: thinker
neural:
  activation: 0.66
  stage: growing
  synapse_in: 20
  synapse_out: 7
---

## Problem

As papers accumulate in the vault, cross-cutting concepts remain implicit — buried in individual notes rather than surfaced as reusable reference entries. Manual concept creation doesn't scale past a few dozen papers.

## Solution

Two-phase automated extraction: scan paper metadata with a Haiku agent to identify recurring concepts, then batch-generate `concepts/*.md` notes with wiki-link backlinks to source papers.

### Phase 1 — Metadata Extraction

Collect title, tags, domain, and summary from all papers into a flat JSON file:

```python
# Extract metadata from frontmatter + body
papers = []
for fname in os.listdir(PAPERS_DIR):
    meta = parse_frontmatter(os.path.join(PAPERS_DIR, fname))
    meta["summary"] = extract_summary_section(content)[:500]
    papers.append(meta)
json.dump(papers, open("/tmp/papers_metadata.json", "w"))
```

### Phase 2 — Concept Identification via Haiku

Send the metadata JSON to a Haiku agent (`max_turns=5`) with instructions to find cross-cutting concepts appearing in 2+ papers:

```
Task(
    subagent_type="general-purpose",
    model="haiku",
    max_turns=5,
    prompt="Read /tmp/papers_metadata.json. Identify 15-25 cross-cutting concepts.
            Return JSON: [{slug, title, definition, papers: [filenames], tags}]"
)
```

**Cost**: ~30K tokens total — metadata is compact, Haiku is cheap.

### Phase 3 — Batch Note Generation

Generate `concepts/{slug}.md` for each concept:

```markdown
---
title: "Concept Title"
date: 2026-02-07
tags: [concept, domain-tag]
---

## Definition
{2-3 sentence definition}

## Context
Appears across {N} papers in the Cohezion vault.

## Related Papers
- [[paper-filename-1]]
- [[paper-filename-2]]

## Related Concepts
See also: [[other-concept]]
```

Skip concepts that already exist. Obsidian's backlinks panel automatically surfaces these connections — any paper that's linked from a concept note will show the concept in its backlinks.

## When to Use

- After batch-importing 10+ new papers (e.g., after a sheets bridge run)
- Periodically (weekly/monthly) to capture emerging themes
- When exploring the vault reveals implicit patterns not yet documented

## When NOT to Use

- For deep, nuanced concept definitions — those should be written manually
- When papers are too heterogeneous to share meaningful concepts
- For fewer than 20 papers — not enough signal for cross-cutting themes

## Key Design Decisions

- **Haiku over Sonnet**: concept identification from structured metadata doesn't need heavy reasoning
- **2+ paper threshold**: ensures concepts are genuinely cross-cutting, not one-off terms
- **Wiki-links in "Related Papers"**: Obsidian's backlinks panel does the reverse linking automatically
- **Slug-based filenames**: consistent with vault conventions, enables `[[concept-slug]]` linking

## Related

- [[compound-engineering]] — concept extraction is a compounding operation
- [[google-sheets-vault-bridge]] — papers often originate from the sheet pipeline

## Decisions & Experiments
- 📋 [[2026-02-09-12d-graph-refined-plan]] - 12D Graph System - Refined Implementation Plan
