---
name: note
description: Create well-structured vault notes with proper frontmatter, templates, and bidirectional links
triggers:
  - user says "create note", "new note", "add note", "write a note about"
  - user invokes /note command
---

# Create Vault Note

Create a new note in the correct vault directory with proper frontmatter, structure, and bidirectional wiki-links.

## Usage

```
/note <type> <title> [description]
```

**Types:** `concept`, `paper`, `decision`, `pattern`, `experiment`, `project`, `inbox`

**Examples:**
- `/note concept reinforcement learning`
- `/note decision switch from REST to GraphQL`
- `/note paper new quantum computing breakthrough`
- `/note pattern retry-with-backoff`

## Execution Steps

### 1. Determine Directory and Template

| Type | Directory | Date Prefix | Required Fields |
|------|-----------|-------------|-----------------|
| concept | `cortex/` | No | title, date, tags |
| paper | `sensory/` | No | title, date, tags |
| decision | `prefrontal/` | Yes (`YYYY-MM-DD-`) | title, date, status, tags |
| pattern | `cerebellum/` | No | title, date, tags |
| experiment | `laboratory/` | Yes (`YYYY-MM-DD-`) | title, date, status, tags |
| project | `motor/` | Yes (`YYYY-MM-DD-`) | title, date, status, tags |
| inbox | `thalamus/` | Yes (`YYYY-MM-DD-`) | title, date |

### 2. Generate Filename

- Slugify the title: lowercase, hyphens for spaces, remove special chars
- Add date prefix where required: `YYYY-MM-DD-slug.md`
- Check for duplicates before creating

### 3. Check for Existing Notes

Before creating, search for existing notes on the same topic:

```bash
# Search by filename similarity
find cortex/ sensory/ prefrontal/ cerebellum/ -name "*keyword*" -type f

# Search by content
grep -rl "keyword" cortex/ sensory/ prefrontal/ cerebellum/ 2>/dev/null
```

If duplicates exist, warn the user and suggest linking instead.

### 4. Build Frontmatter

Use the directory's required fields. Tags MUST be arrays:

```yaml
---
title: "Note Title"
date: YYYY-MM-DD
status: proposed  # only for decisions, experiments, projects
tags: [tag1, tag2, tag3]
related_concepts: [concept1, concept2]  # for concepts
---
```

**Tag guidelines:**
- Use existing vault tags where possible (check other notes in same directory)
- Include the type tag (e.g., `concept`, `decision`, `pattern`)
- Add 2-4 domain tags from the note's subject matter
- Use lowercase, hyphenated multi-word tags

### 5. Build Content Structure

**Concept notes:**
```markdown
## Definition
[Clear, concise definition — 2-3 sentences]

## Key Properties
- [Property 1]
- [Property 2]

## Examples
- [Concrete example 1]
- [Concrete example 2]

## Related Papers
- [[paper-name]]

## Related Concepts
- [[concept-name]]

## Relevance to Cohezion
[How this concept connects to the Cohezion framework]
```

**Decision notes (ADR format):**
```markdown
## Context
[What prompted this decision]

## Decision
[What was decided]

## Consequences
[What follows from this decision]

## Alternatives Considered
[What else was evaluated]
```

**Pattern notes:**
```markdown
## Problem
[What problem does this solve]

## Solution
[The reusable approach]

## Code Example
[Implementation with code block]

## When to Use
[Applicability guidelines]

## When NOT to Use
[Counter-indications]
```

**Paper notes:**
```markdown
## Summary
[2-3 sentence summary of the paper/finding]

## Key Findings
- [Finding 1]
- [Finding 2]

## Methodology
[How the research was conducted]

## Implications
[Why this matters]

## Related Papers
- [[related-paper]]

## Related Concepts
- [[related-concept]]
```

### 6. Add Bidirectional Links

After creating the note:

1. Identify 3-5 existing notes that relate to this topic
2. Add `[[wiki-links]]` in the new note's Related sections
3. Add a backlink `[[new-note]]` in each related note's Related section

This maintains the vault's bidirectional linking convention.

### 7. Research Content (When Requested)

If the user provides a topic but no content:

1. Use WebSearch to find authoritative information
2. Use Context7 if the topic relates to a library/framework
3. Write structured content following the template
4. Include Primary Sources section with real URLs
5. Never fabricate citations — only include sources you actually found

### 8. Verify

- Frontmatter is valid YAML
- Tags are arrays
- Wiki-links point to existing notes (or flag as new stubs)
- File is in the correct directory
- No duplicate notes exist

## Notes

- Always check for existing notes before creating new ones
- Prefer linking to existing notes over creating duplicates
- When creating concept stubs for links, use the minimal concept template
- Today's date for the `date` field: use current date from system
