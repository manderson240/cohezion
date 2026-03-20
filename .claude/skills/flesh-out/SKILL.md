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

---

## Thin Note Expansion (Non-Stub Notes Under 3KB)

During vault-keeper maintenance cycles, the target is notes that have real content but are too short — not auto-generated stubs, but embryo-stage notes that need depth. Use this section alongside the stub expansion workflow above.

### Finding Thin Notes

```bash
# Find real (non-template) notes under 3KB in priority directories
find cortex/ cerebellum/ laboratory/ sensory/ motor/ \
  -maxdepth 2 -name '*.md' ! -name '_template.md' ! -name '_index.md' \
  -size -3k 2>/dev/null | xargs wc -c 2>/dev/null | sort -n | grep -v total
```

### Skip List (Brief by Design)

| Directory / Pattern | Reason to Skip |
|---------------------|----------------|
| `prefrontal/` ADRs | Intentionally concise decision records |
| `cerebellum/lessons/` | Lesson-format notes are fine at 800-1200 bytes |
| `cerebellum/domains/testing/` | Test artifact stubs, not knowledge notes |
| Notes < 10 lines with no real content | Investigate before expanding — may be test artifacts |

### Type-Specific Expansion Templates

#### Cerebellum Pattern Notes (`cerebellum/*.md`, `aspect: thinker`)

Pattern notes describe reusable solutions. Embryo-stage ones have the skeleton but no depth. Expand to 4-6KB with:

```markdown
## Problem
[Keep existing — ensure it's specific, not generic]

## Solution
[Keep existing skeleton]

## [Protocol / Schema / Implementation Details]
[New section — the deep detail: SurrealDB schema, algorithm steps, code block with full YAML/Python]

## Failure Modes

| Failure | Symptom | Recovery |
|---------|---------|----------|
| [specific failure] | [how it manifests] | [how to fix] |

## When to Use
[Keep/expand existing]

## Cohezion Relevance
[New section — how this pattern directly enables Cohezion capabilities; reference specific vault notes, projects, or metrics]

## Related
[Expand to 5+ links: existing + [[multi-agent-systems]], [[surrealdb]], [[workflow-orchestration]], etc.]
```

**Quality bar:** After expansion, each Related link should have an annotation explaining the specific connection (not just the note title).

#### Laboratory Experiment Notes (`laboratory/*.md`, `aspect: thinker`)

Experiment notes have Hypothesis/Method/Results/Learnings. Embryo-stage ones have thin results. Expand to 3-4KB with:

```markdown
## Hypothesis
[Keep existing]

## Method
[Keep existing]

## Results (Detailed)
[New: add tables, cascade failure chains, diagnosis commands, before/after comparisons]

## [Root Cause Chain / Diagnosis Commands] (if debugging)
[New section for debugging experiments — the exact commands that worked, the causal chain that led to the bug]

## Learnings
[Expand from 3 bullets to 5-7, with specific actionable rules, not general observations]

## Cohezion Relevance
[New section — which Cohezion principle or lesson this validates]

## Related
[Add: relevant lessons [[lesson-XX-*]], related patterns, downstream ADRs]
```

### Post-Expansion Verification

After expanding a batch of thin notes, verify they crossed the 3KB threshold:

```bash
for f in path/to/note1.md path/to/note2.md; do
  sz=$(wc -c < "$f")
  echo "$(basename $f): ${sz} bytes"
done
```

### Graph-Alerts Refresh Insight

After completing orphan healing and synapse gap work (Phase 3 of vault-keeper), re-read `metabolism/graph-alerts.md`. The GraphReactor runs continuously and typically updates within minutes of edits. The refreshed file will:
- Confirm healed orphans are no longer listed (verification)
- Reveal new orphans and synapse gaps exposed by the edits (next targets)

This means Phase 3 and Phase 4 of vault-keeper are iterative — each pass can expose new work.

### Orphan Healing Verification Command

```bash
# Verify healed orphans now have inbound links
for note in "note-name-1" "note-name-2" "note-name-3"; do
  count=$(grep -rl "\[\[.*$note" \
    cortex/ sensory/ prefrontal/ cerebellum/ motor/ memory/ Agents/ 2>/dev/null \
    | grep -v "/$note.md" | wc -l)
  echo "$note: $count inbound"
done
# Expect > 0 for each healed orphan
```
