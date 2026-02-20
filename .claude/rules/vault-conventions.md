# Vault Conventions

Standards for working with notes in the Cohezion vault.

## Frontmatter Schema

All notes use YAML frontmatter. **Tags must be arrays**, not strings.

```yaml
---
title: Note Title
date: 2026-02-19
status: active
tags: [decision, architecture]
---
```

### Required Fields by Directory

| Directory      | Required Fields                  |
|----------------|----------------------------------|
| `decisions/`   | title, date, status, tags        |
| `experiments/` | title, date, status, tags        |
| `patterns/`    | title, date, tags                |
| `projects/`    | title, date, status, tags        |
| `papers/`      | title, date, tags                |

### Status Values

- **Decisions:** `proposed`, `accepted`, `rejected`, `deprecated`
- **Experiments:** `in-progress`, `complete`, `failed`
- **Projects:** `active`, `complete`, `archived`

## Cross-Referencing

Use Obsidian wiki-links for cross-references:

```markdown
See [[2026-02-14-phase-completion-pattern]] for details.

Related to [[operational-principle-no-destructive-operations]].
```

**Rules:**
- Use full note name including date prefix
- Link at first mention of a concept
- Keep links atomic (one concept per note)

## Directory Templates

Templates are named `_template.md` in each directory:
- `decisions/_template.md`
- `experiments/_template.md`
- `patterns/_template.md`

**When creating notes:** Copy template, fill sections, update frontmatter.

## Note Organization

### Inbox Workflow

1. **Capture** - Drop new ideas in `inbox/`
2. **Triage** - Review weekly, research thoroughly
3. **Move** - Relocate to appropriate directory with frontmatter
4. **Link** - Cross-reference related notes

### Naming Conventions

**Include date prefix for temporal notes:**
- `decisions/2026-02-19-feature-name.md`
- `experiments/2026-02-19-hypothesis-test.md`
- `daily/2026-02-19-session-173cdb02.md`

**No date prefix for timeless content:**
- `patterns/safe-file-split-checklist.md`
- `concepts/cohezion-framework.md`

## 3D Graph Data

The 3D graph plugin loads data from:
```
.claude/3d-graph-data.json
```

**When adding papers:**
1. Add frontmatter with proper tags
2. Regenerate graph data: `.claude/extract_3d_graph.py`
3. Reload plugin in Obsidian

## Common Mistakes

**Bad:** `tags: decision, architecture` (comma-separated string)
**Good:** `tags: [decision, architecture]` (YAML array)

**Bad:** `[[note]]` without date prefix when note has one
**Good:** `[[2026-02-19-note]]` (full name)

**Bad:** Creating notes directly in final location without template
**Good:** Use inbox, then move with proper frontmatter
