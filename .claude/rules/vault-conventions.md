# Vault Conventions — Triune Self Architecture

Standards for working with notes in the Cohezion vault.

## Frontmatter Schema

All notes use YAML frontmatter. **Tags must be arrays**, not strings.

```yaml
---
title: Note Title
date: 2026-03-09
status: active
tags: [topic, subtopic]
aspect: knower          # knower | thinker | doer | connective
---
```

### Required Fields by Directory

| Directory        | Required Fields                         |
|------------------|-----------------------------------------|
| `cortex/`        | title, date, tags, aspect               |
| `sensory/`       | title, date, tags, aspect               |
| `memory/`        | title, date, tags, aspect, severity     |
| `genome/`        | title, date, tags, aspect               |
| `prefrontal/`    | title, date, status, tags, aspect       |
| `laboratory/`    | title, date, status, tags, aspect       |
| `cerebellum/`    | title, date, tags, aspect               |
| `motor/`         | title, date, status, tags, aspect       |
| `hippocampus/`   | title, date, tags                       |
| `thalamus/`      | title (minimum — triage adds the rest)  |

### Aspect Assignment

| Aspect | Directories |
|--------|-------------|
| `knower` | cortex, sensory, memory, genome |
| `thinker` | prefrontal, laboratory, cerebellum, benchmarks |
| `doer` | motor, hippocampus, thalamus, missions, retrospectives, Agents |
| `connective` | dreaming, songlines, subconscious, metabolism, visual-cortex |

### Status Values

- **prefrontal/:** `proposed`, `accepted`, `rejected`, `deprecated`
- **laboratory/:** `in-progress`, `complete`, `failed`
- **motor/:** `active`, `complete`, `archived`

## Cross-Referencing

Use Obsidian wiki-links: `[[note-name]]`

- Use bare filename (no path prefix): `[[machine-learning]]` not `[[cortex/machine-learning]]`
- Link at first mention of a concept
- Keep links atomic (one concept per note)

## Directory Templates

Templates are named `_template.md` in each directory:
- `prefrontal/_template.md`
- `laboratory/_template.md`
- `cerebellum/_template.md`

## Note Organization

### Thalamus Workflow (was Inbox)

1. **Capture** - Drop new ideas in `thalamus/`
2. **Triage** - Review weekly, research thoroughly
3. **Move** - Relocate to correct aspect directory with frontmatter
4. **Link** - Cross-reference related notes

### Naming Conventions

**Include date prefix for temporal notes:**
- `prefrontal/2026-03-09-feature-name.md`
- `laboratory/2026-03-09-hypothesis-test.md`
- `hippocampus/2026-03-09-session-173cdb02.md`

**No date prefix for timeless content:**
- `cerebellum/safe-file-split-checklist.md`
- `cortex/cohezion-framework.md`

## Common Mistakes

**Bad:** `tags: decision, architecture` (comma-separated string)
**Good:** `tags: [decision, architecture]` (YAML array)

**Bad:** Missing `aspect:` field on new notes
**Good:** Always include `aspect:` matching the directory zone

**Bad:** Creating notes directly in final location without template
**Good:** Use `thalamus/`, then move with proper frontmatter
