---
name: vault-health
description: Audit vault integrity — broken links, orphan notes, stubs, frontmatter issues, and provide actionable fix recommendations
triggers:
  - user says "vault health", "audit vault", "check vault", "vault maintenance"
  - user invokes /vault-health command
---

# Vault Health Audit

Run a comprehensive health check on the Obsidian vault, surfacing issues that degrade navigation, discoverability, and knowledge graph density.

## When to Use

- Periodic vault maintenance (weekly/monthly)
- After bulk imports or automated linking runs
- Before presentations or knowledge sharing
- When the graph view looks sparse or disconnected

## Execution Steps

### 1. Broken Wiki-Links

Find links pointing to non-existent notes:

```bash
# Extract all wiki-links, check which targets don't exist as files
grep -roh '\[\[[^]]*\]\]' cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ 2>/dev/null \
  | sed 's/\[\[//;s/\]\]//' | sort -u | while read link; do
  # Handle display text: [[target|display]] -> target
  target="${link%%|*}"
  fname="${target}.md"
  found=0
  for d in concepts papers decisions patterns experiments projects inbox daily; do
    [ -f "$d/$fname" ] && found=1 && break
  done
  [ $found -eq 0 ] && echo "$link"
done
```

Report: total count, top 10 examples, which directories have the most broken links.

### 2. Orphan Notes (No Inbound Links)

Find notes that no other note links to:

```bash
# For each .md file, check if any other file links to it
for dir in concepts papers decisions patterns experiments projects; do
  for f in "$dir"/*.md; do
    [ -f "$f" ] || continue
    basename="${f##*/}"
    name="${basename%.md}"
    # Count inbound links (excluding self-references)
    count=$(grep -rl "\[\[$name" cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ 2>/dev/null | grep -v "$f" | wc -l)
    [ "$count" -eq 0 ] && echo "ORPHAN: $f"
  done
done
```

Report: total orphan count by directory, list them.

### 3. Stub Notes

Find auto-generated stubs that need content:

```bash
grep -rl 'Auto-generated stub\|Add.*definition.*here\|\[Add.*here\]' cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ 2>/dev/null
```

Report: total count, list by directory.

### 4. Frontmatter Issues

Check for common frontmatter problems:

```bash
# Missing frontmatter entirely
for dir in concepts papers decisions patterns experiments projects; do
  for f in "$dir"/*.md; do
    [ -f "$f" ] || continue
    head -1 "$f" | grep -q '^---' || echo "NO_FRONTMATTER: $f"
  done
done

# Tags as string instead of array
grep -rl '^tags:' cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ 2>/dev/null | while read f; do
  grep '^tags:' "$f" | grep -qv '\[' && echo "TAGS_NOT_ARRAY: $f"
done

# Missing required fields per directory
# prefrontal/ needs: title, date, status, tags
# cortex/ needs: title, date, tags
```

### 5. Large Files

Check for files exceeding reasonable size:

```bash
find cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ -name '*.md' -size +50k -exec ls -lh {} \;
```

### 6. Summary Report

Present results as a structured report:

```markdown
## Vault Health Report — YYYY-MM-DD

| Metric | Count | Status |
|--------|-------|--------|
| Total notes | X | — |
| Broken wiki-links | X | 🔴/🟡/🟢 |
| Orphan notes | X | 🔴/🟡/🟢 |
| Stub notes | X | 🟡 |
| Frontmatter issues | X | 🔴/🟡/🟢 |
| Oversized files | X | 🟡 |
| Wiki-link density | X links / note avg | — |

### Recommended Actions
1. [Highest priority fix]
2. [Second priority]
3. [Third priority]

Use `/link` to add missing connections.
Use `/flesh-out` to expand stub notes.
Use `/triage` to process inbox items.
```

## Thresholds

| Metric | Green | Yellow | Red |
|--------|-------|--------|-----|
| Broken links | < 10 | 10-50 | > 50 |
| Orphan notes | < 5% | 5-15% | > 15% |
| Stubs | < 10 | 10-30 | > 30 |
| Frontmatter issues | 0 | 1-10 | > 10 |

## Notes

- This skill is read-only — it reports issues but does not fix them
- Use other skills (`/link`, `/flesh-out`, `/triage`) to act on findings
- Run after bulk operations to verify vault integrity
- Results can be saved to `hippocampus/` as a maintenance log
