---
name: triage
description: Process inbox notes — research, structure, and move to the correct vault directory with proper frontmatter and links
triggers:
  - user says "triage inbox", "process inbox", "sort inbox", "clean inbox"
  - user invokes /triage command
---

# Triage Inbox Notes

Process notes from `thalamus/` into their permanent homes — researching topics, adding structure, applying frontmatter, and creating cross-links.

## Usage

```
/triage [options]
```

- `/triage` — Process all inbox notes
- `/triage thalamus/note-name.md` — Process a specific note
- `/triage --dry-run` — Show what would happen without making changes

## Execution Steps

### 1. Scan Inbox

```bash
ls -la thalamus/*.md 2>/dev/null
```

List all notes with their sizes. Skip non-markdown files.

### 2. For Each Note, Classify

Read the note content and determine:

| Classification | Target Directory | Criteria |
|---------------|-----------------|----------|
| **Concept** | `cortex/` | Defines a term, idea, or technology |
| **Paper/Research** | `sensory/` | Summarizes research, findings, or external source |
| **Decision** | `prefrontal/` | Records an architectural or strategic choice |
| **Pattern** | `cerebellum/` | Describes a reusable solution to a problem |
| **Experiment** | `laboratory/` | Documents a hypothesis test or trial |
| **Project** | `motor/` | Tracks ongoing work or initiative |
| **Discard** | (delete) | Empty, duplicate, or no longer relevant |

If classification is ambiguous, ask the user.

### 3. Research and Expand

For each note being triaged:

1. **Read existing content** — Understand what the user captured
2. **Research the topic** — Use WebSearch to find authoritative information
3. **Write structured content** following the target directory's template:
   - Concepts: Definition, Key Properties, Examples, Related
   - Papers: Summary, Key Findings, Methodology, Implications
   - Decisions: Context, Decision, Consequences, Alternatives
   - Patterns: Problem, Solution, Code Example, When to Use
4. **Preserve user's original notes** — Incorporate their observations, don't overwrite
5. **Add Primary Sources** — Include real URLs from research

### 4. Build Frontmatter

Apply the target directory's required fields:

```yaml
---
title: "Properly Cased Title"
date: YYYY-MM-DD  # use original date if present, otherwise today
status: active    # for prefrontal/laboratory/projects
tags: [type-tag, domain-tag1, domain-tag2]
related_concepts: [concept1, concept2]  # for concept notes
---
```

**Tag rules:**
- Check existing vault tags first: `grep -roh 'tags: \[.*\]' cortex/ sensory/ | sort -u`
- Reuse established tags where possible
- Tags must be YAML arrays

### 5. Generate Filename

- Slugify the title: lowercase, hyphens, no special chars
- Add date prefix for temporal notes (decisions, experiments, projects)
- Check for filename collisions

### 6. Find and Add Links

Before moving the note:

1. Search vault for related notes by topic/tags
2. Add `[[wiki-links]]` to Related sections in the new note
3. Add backlinks in related notes pointing to the new note

### 7. Move the Note

1. Write the structured note to the target directory
2. Delete the original from `thalamus/`
3. Verify the file exists in its new location

### 8. Report

```markdown
## Triage Report

| Inbox Note | Action | Destination | Links Added |
|------------|--------|-------------|-------------|
| note-1.md | Moved | cortex/topic.md | 4 |
| note-2.md | Moved | sensory/research.md | 3 |
| note-3.md | Discarded | — | — |

**Processed:** X notes
**Moved:** Y notes
**Discarded:** Z notes
**Links created:** N bidirectional pairs
```

## Batch Processing

When processing multiple inbox notes:

1. Classify all notes first (show the plan)
2. Process in order: concepts first (they're link targets), then papers, then decisions
3. This ordering maximizes bidirectional linking opportunities

## Quality Checks

Before marking triage complete:

- [ ] All frontmatter is valid YAML with array tags
- [ ] No duplicate notes in target directory
- [ ] At least 2-3 wiki-links added per note
- [ ] Content is substantive (not just a stub)
- [ ] Original inbox note is deleted
- [ ] Backlinks added in related notes

## Notes

- Preserve the user's original insight/observation — it's the seed
- Research supplements the user's note, doesn't replace it
- If a note is too vague to classify, ask the user before guessing
- Empty inbox notes (just a title) should be treated as concept stubs — research and expand
- The goal is zero inbox — all notes processed and properly filed
