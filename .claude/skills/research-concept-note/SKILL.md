---
name: research-concept-note
description: |
  Create a deeply-researched concept note with real mathematics, primary sources,
  and full bidirectional vault integration. Use when: (1) user asks "do we have
  [physics/science topic]?", (2) creating concept notes from scratch (not stubs),
  (3) adding a new domain to cortex/ that needs integration with MOCs and
  existing notes. Covers the full loop: research → write → backlink → MOC update.
author: Claude Code
version: 1.0.0
---

# Research Concept Note

Full workflow for creating mathematically rigorous concept notes with primary sources
and bidirectional vault integration.

## When to Use

- User asks "do we have X?" for a science/physics/technical topic
- Creating concept notes that need real equations, not just prose summaries
- New topics that should connect to existing MOCs and concept notes

## Workflow

### Step 1: Check Existing Coverage

```bash
# Check if note already exists
ls cortex/*topic* 2>/dev/null

# Check if existing notes reference this topic
rg -l "\[\[topic-name\]\]" cortex/ sensory/
```

If stubs exist, use `/flesh-out` instead.

### Step 2: Research Primary Sources

Use WebSearch (NOT WebFetch for social media/Reddit — those are blocked):

```
WebSearch: "topic site:arxiv.org OR site:journals.aps.org"
WebSearch: "topic peer reviewed landmark paper"
WebSearch: "topic textbook author year"
```

Collect 3-6 primary sources with full citations:
- Author(s), Year, Title, Journal, Volume, Page/DOI

**Note:** Reddit/social media URLs fail in WebFetch. Use WebSearch to find the
underlying papers referenced.

### Step 3: Write the Note

**File:** `cortex/topic-name.md`

**Required sections:**

```markdown
---
title: "Topic Name"
date: YYYY-MM-DD
tags: [concept, domain, subtopic]
aspect: knower
neural:
  activation: 0.750
  stage: growing
  cluster: concepts
---

# Topic Name

## Definition
[2-3 sentences on what it IS]

## Key Properties

### [Subtopic 1]
Real equations with LaTeX-style notation:
> F = ma
> E = mc²

Explain each term. Use tables for properties.

### [Subtopic 2]
...

## Mathematical Framework

Key equations with derivation context:
> [equation with variables defined below]

where [variable definitions].

## Examples
- Concrete real-world examples with measurements
- Laboratory demonstrations
- Astronomical/natural examples

## Primary Sources
- Author, A. (Year). "Title." *Journal*, Vol(Issue), pages.
- [3-6 peer-reviewed sources minimum]

## Related Concepts
- [[related-note-1]] — one-line description of relationship
- [[related-note-2]] — ...

## Relevance to Cohezion
[Map the physics/concept to Triune Vault architecture:
- How does it relate to Knower/Thinker/Doer?
- What is the Aboriginal layer analogue?
- How does it relate to HIHO coherence, Songlines, Countries?
- What does the math map to in vault terms?]
```

### Step 4: Find Notes That Should Link Back

```bash
# Find notes that mention this topic
rg -l "topic-name\|TopicName\|topic name" cortex/ sensory/ --ignore-case

# Find notes in the same domain
rg -l "\[\[related-concept\]\]" cortex/

# Check MOC files
rg -l "domain" cortex/MOC-*.md
```

### Step 5: Add Backlinks to Existing Notes

For each existing note that is semantically related, add a `[[new-topic]]` link
in its "Related Concepts" section.

**Edit tool requires EXACT string match — watch for:**
- `--` (double hyphen) vs `—` (em dash) in existing files
- Trailing spaces or different line endings
- Read the section first to get the exact surrounding text

```
# Pattern: read the section, then edit with exact match
Read existing-note.md → find exact text → Edit with that exact text as old_str
```

Typical candidates for backlinks:
- Notes in the same physics domain
- Notes that are conceptually "parent" topics
- Notes in MOCs that cover this domain

### Step 6: Update MOCs

Identify which MOCs cover this domain and add the new note:

```bash
ls cortex/MOC-*.md
```

Add to "Core Concepts" section of relevant MOC(s):
```markdown
- [[new-topic-name]] — brief one-line description
```

## Quality Checklist

- [ ] Real equations (not just prose descriptions)
- [ ] 3+ peer-reviewed primary sources with full citations
- [ ] "Relevance to Cohezion" section mapping to Triune architecture
- [ ] `aspect: knower` in frontmatter (cortex/ notes are Knower aspect)
- [ ] `neural:` block with activation, stage, cluster
- [ ] Bidirectional links: new note links out AND existing notes link back
- [ ] At least 1 MOC updated
- [ ] No broken `[[links]]` — only link to notes that exist or are being created

## Common Pitfalls

1. **Reddit/social media URLs** — WebFetch cannot access these. Use WebSearch to
   find the original papers being discussed.

2. **Edit string mismatch** — The Edit tool requires exact character-for-character
   match. Always Read the file first and copy the exact surrounding text.

3. **Orphan notes** — A note with no backlinks from existing notes is isolated.
   Always do Steps 4-5 to integrate it.

4. **MOC gaps** — Forgetting to update the MOC leaves the note invisible to
   readers navigating by MOC.
