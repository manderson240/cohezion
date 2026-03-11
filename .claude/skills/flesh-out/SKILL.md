---
name: flesh-out
description: Expand stub notes with researched, structured content while preserving existing links and frontmatter
triggers:
  - user says "flesh out", "expand stubs", "fill in stubs", "expand notes", "research stubs"
  - user invokes /flesh-out command
---

# Flesh Out Stub Notes

Find auto-generated stub notes and expand them with researched, well-structured content. Stubs are placeholders created during linking runs — they have frontmatter and maybe a title but no real content.

## Usage

```
/flesh-out [options]
```

- `/flesh-out` — Find and expand stubs across the vault (interactive — confirms before each)
- `/flesh-out cortex/topic.md` — Expand a specific stub
- `/flesh-out cortex/` — Expand all stubs in a directory
- `/flesh-out --list` — Just list stubs without expanding
- `/flesh-out --batch N` — Expand up to N stubs non-interactively

## Execution Steps

### 1. Find Stubs

```bash
# Notes with auto-generated stub markers
grep -rl 'Auto-generated stub\|\[Add.*here\]\|Add definition here' \
  cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ 2>/dev/null
```

Sort by priority:
1. **High inbound links** — stubs that many notes link to (most impactful to flesh out)
2. **Core concepts** — stubs in `cortex/` (they're link hubs)
3. **Recent stubs** — created in the last 30 days

### 2. Assess Each Stub

Read the stub to understand:
- What title/topic it covers
- What frontmatter (tags, related_concepts) already exists
- Which notes link TO this stub (inbound links provide context)
- What the linking context tells us about expected content

```bash
# Find notes that link to this stub
name="stub-name"
grep -rl "\[\[$name" cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ 2>/dev/null
```

Read the linking context in those notes to understand what content is expected.

### 3. Research the Topic

Based on the stub's title, tags, and linking context:

1. **WebSearch** for authoritative definitions and current information
2. **Context7** if it's a library, framework, or technical tool
3. **Read related vault notes** for Cohezion-specific context
4. **Check sensory/** for research that discusses this concept

### 4. Write Content

Follow the directory's template structure. For concept stubs (most common):

```markdown
## Definition

[2-3 sentences. Clear, concise, citing authoritative sources where possible.]

## Key Properties

- [Property 1 — specific, not generic]
- [Property 2]
- [Property 3]

## Examples

- [Concrete example 1 with specifics]
- [Concrete example 2]

## Primary Sources

- Author (Year). *Title*. [URL](URL)

## Related Papers

- [[existing-paper-link]] — [brief annotation if not obvious]

## Related Concepts

- [[existing-concept-link]]

## Relevance to Cohezion

[1-2 sentences connecting this concept to the Cohezion framework.
How would Cohezion agents use, implement, or encounter this concept?]
```

### 5. Preserve Existing Content

**Critical:** Do not overwrite existing frontmatter, links, or content.

- Keep all existing `tags`, `related_concepts`, and other frontmatter fields
- Keep all existing `[[wiki-links]]` — add to them, don't replace
- If the stub has ANY user-written content, incorporate it
- Only replace placeholder text like `[Add definition here]` and `> Auto-generated stub`

### 6. Add New Links

After writing content:

1. Identify 3-5 related notes that should link to/from this note
2. Add outbound `[[wiki-links]]` in the appropriate sections
3. Add backlinks in related notes (bidirectional)
4. Verify all link targets exist

### 7. Verify Quality

Before marking a stub as complete:

- [ ] Definition is accurate and sourced
- [ ] Content is substantive (not just rephrased title)
- [ ] Frontmatter preserved and valid
- [ ] Tags are arrays
- [ ] At least 3 outbound wiki-links
- [ ] Relevance to Cohezion section present
- [ ] No placeholder text remains
- [ ] Primary sources included (real URLs)

### 8. Report

```markdown
## Flesh-Out Report

**Stubs found:** X
**Expanded this session:** Y
**Remaining:** Z

### Expanded Notes:
| Note | Inbound Links | Outbound Links Added | Sources |
|------|--------------|---------------------|---------|
| cortex/topic.md | 5 | 4 | 2 |

### High-Priority Remaining Stubs:
| Note | Inbound Links | Priority |
|------|--------------|----------|
| cortex/important.md | 12 | High |
```

## Prioritization

When choosing which stubs to expand first:

1. **Link hubs** — Stubs with 5+ inbound links (expanding these has the most graph impact)
2. **Core domain concepts** — Concepts central to Cohezion (agentic AI, MCP, knowledge graphs)
3. **Recently created** — Stubs from the current sprint
4. **Cross-domain bridges** — Concepts that connect different knowledge domains

## Quality Standards

**Good expansion:**
- Accurate, sourced definitions
- Specific examples (not generic)
- Cohezion relevance that's genuine, not forced
- Links to notes that are truly related

**Bad expansion (avoid):**
- Generic Wikipedia-style content with no specificity
- Fabricated sources or URLs
- Forced Cohezion connections that don't make sense
- Expanding every stub with the same boilerplate

## Notes

- Expanding 5-10 high-impact stubs per session is more valuable than doing 50 shallow expansions
- If a stub topic is too niche or obscure, it may be better to merge it into a parent concept
- Some stubs may be better deleted than expanded (if the concept is too granular)
- Always verify WebSearch sources are real before including them
