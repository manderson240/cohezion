---
name: link
description: Find and add missing bidirectional wiki-links across vault notes to densify the knowledge graph
triggers:
  - user says "link notes", "add links", "connect notes", "densify graph", "find connections"
  - user invokes /link command
---

# Link Vault Notes

Analyze vault notes to discover and add missing bidirectional wiki-links, increasing knowledge graph density and discoverability.

## Usage

```
/link [scope] [options]
```

**Scopes:**
- `/link <note-path>` — Link a single note to related notes
- `/link cortex/` — Link all notes in a directory
- `/link --stale` — Find notes with zero or few outbound links
- `/link --orphans` — Focus on notes with no inbound links

## Execution Steps

### 1. Identify Candidates

**For a single note:**
- Read the note's content, tags, and related_concepts
- Search for notes that share tags, concepts, or subject matter
- Look for notes that mention the same entities or topics

**For a directory:**
- Process notes in batches of 10-20
- Focus on notes with < 3 outbound wiki-links first (highest ROI)

**For orphans:**
```bash
# Find notes with no inbound links
for dir in concepts papers decisions patterns experiments projects; do
  for f in "$dir"/*.md; do
    [ -f "$f" ] || continue
    name="${f##*/}"; name="${name%.md}"
    count=$(grep -rl "\[\[$name" cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ 2>/dev/null | grep -v "$f" | wc -l)
    [ "$count" -eq 0 ] && echo "$f"
  done
done
```

### 2. Discover Connections

For each note, find related notes using multiple strategies:

**A. Tag-based matching:**
```bash
# Find notes sharing tags with the target
# Extract tags from target, search for them in other notes
```

**B. Content-based matching:**
- Read the note's Definition/Summary section
- Identify key terms and entities
- Search vault for notes mentioning those terms

**C. Related concepts field:**
- Check `related_concepts` frontmatter
- Find concept notes matching those names
- Check if wiki-links already exist

**D. Semantic proximity:**
- Notes in the same domain (shared tag prefixes)
- Papers citing similar concepts
- Decisions affecting similar systems

### 3. Validate Links

Before adding a link, verify:

1. **Target exists** — The linked note must exist as a file
2. **Not self-referencing** — Don't link a note to itself
3. **Not already linked** — Check existing `[[wiki-links]]` in the note
4. **Meaningful connection** — The relationship should be substantive, not superficial

### 4. Add Links

**Where to place links in each note type:**

| Note Type | Link Section | Format |
|-----------|-------------|--------|
| Concept | `## Related Concepts` and `## Related Papers` | `- [[note-name]]` |
| Paper | `## Related Papers` and `## Related Concepts` | `- [[note-name]]` with optional annotation |
| Decision | End of note or `## Related` section | `- [[note-name]]` |
| Pattern | `## Related Patterns` section | `- [[note-name]]` |

**Link with context** when the relationship isn't obvious:
```markdown
- [[quantum-computing]] — this concept's error correction approach parallels the retry patterns described here
```

### 5. Ensure Bidirectionality

**Critical:** When adding `[[B]]` to note A, also add `[[A]]` to note B.

```
# In note A:
## Related Concepts
- [[B]]

# In note B:
## Related Concepts
- [[A]]
```

If note B doesn't have a Related section, create one.

### 6. Report Results

After linking:

```markdown
## Linking Report

**Notes processed:** X
**New links added:** Y (Z bidirectional pairs)

### Links Added:
| Source | Target | Reason |
|--------|--------|--------|
| concept-a | concept-b | Shared tag: quantum-computing |
| paper-x | concept-a | Paper discusses concept directly |

### Still Orphaned:
- notes that couldn't find good connections
```

## Quality Guidelines

**Good links:**
- Two notes discuss the same concept from different angles
- A paper provides evidence for a concept
- A decision references a pattern or concept
- An experiment tests a concept described elsewhere

**Bad links (avoid):**
- Linking every AI note to every other AI note
- Superficial tag-only connections with no content relationship
- Linking to stubs that have no content

## Batch Processing

When processing an entire directory:

1. Read all notes, build an in-memory map of topics and tags
2. Identify link candidates by cross-referencing
3. Prioritize: orphans first, then low-link-count notes
4. Add links in batches, verify each one
5. Report summary statistics

## Notes

- Aim for 3-8 outbound links per note (concept/paper)
- Decision notes may have fewer links (1-3)
- Pattern notes should link to concepts they implement
- Always verify the target note exists before adding a link
- Use `[[note-name]]` format (no directory prefix needed — Obsidian resolves by filename)
