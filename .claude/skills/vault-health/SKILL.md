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

### 0. Baseline Metrics

```bash
# Total notes
find . -name "*.md" -not -path "./.obsidian/*" -not -path "./.claude/*" \
  -not -path "*/node_modules/*" -not -path "*/.worktrees/*" -not -path "./.git/*" | wc -l

# Wiki-links
rg -o '\[\[[^\]]+\]\]' --type md 2>/dev/null | wc -l
```

### 1. Orphan Notes (No Inbound Links)

Use the Python-based scanner — shell grep is O(n²) and too slow on 1600+ notes:

```bash
python3 -c "
import os, re

# Skip meta/tooling directories
SKIP = ['.obsidian', '.claude', 'node_modules', '.worktrees', '.git', 'tools', 'obsidian-plugin', 'mcp-server']

# Build note registry: filename-stem → filepath
notes = {}
for root, dirs, files in os.walk('.'):
    if any(p in root for p in SKIP):
        continue
    for f in files:
        if f.endswith('.md') and not f.startswith('_'):
            notes[f[:-3]] = os.path.join(root, f)

# Count inbound links for every note (single pass over all files)
inbound = {name: 0 for name in notes}
link_pat = re.compile(r'\[\[([^\]|#]+)')

for name, path in notes.items():
    try:
        with open(path) as fh:
            for m in link_pat.finditer(fh.read()):
                target = m.group(1).strip()
                if target in inbound:
                    inbound[target] += 1
    except:
        pass

# Report orphans by directory (most impactful dirs first)
for directory in ['prefrontal', 'cortex', 'cerebellum', 'laboratory', 'sensory', 'memory', 'motor']:
    orphans = [(n, notes[n]) for n in notes
               if notes[n].startswith('./' + directory + '/')
               and inbound[n] == 0]
    orphans.sort()
    if orphans:
        print(f'{directory}: {len(orphans)} orphans')
        for name, path in orphans[:10]:
            size = os.path.getsize(path)
            print(f'  {name} ({size}B)')
"
```

**Key insight:** Link aliases `[[target|display text]]` are handled — the regex captures only the target part (before `|` or `#`). The single-pass approach reads each file once and indexes all outbound links, making it O(n) rather than O(n²).

**Bare-name links required when fixing orphans:** The orphan scanner keys notes by bare
filename stem (`index`, `SETUP_GUIDE`). When adding inbound links to fix orphans, you MUST
use bare names — `[[index|CS249R Book]]` — not path-prefixed — `[[cs249r/index|CS249R Book]]`.
Path-prefixed links (`cs249r/index`) don't match the key `index` in the inbound-count dict,
so the orphan remains uncounted. Always use bare filenames per vault conventions, and always
re-run the orphan scanner after fixing to confirm counts dropped to 0.

### False Positive Filter (Run Before Acting on Orphan Alerts)

SurrealDB `synapse_in` metadata can be severely stale. Before treating any note as orphaned
based on graph alerts or frontmatter `synapse_in: 0`, verify with actual grep:

```bash
# For each suspected orphan, check actual inbound wiki-link count
NOTE_STEM="note-filename-without-extension"
rg -l "\[\[$NOTE_STEM" --type md | grep -v "$NOTE_STEM.md" | wc -l
```

If the count is > 0, the note is NOT orphaned — update its `synapse_in` frontmatter to match
reality and skip it.

**Common false positive sources:**

| Source | Example | Action |
|--------|---------|--------|
| Stale SurrealDB `synapse_in: 0` | Note has 57 actual inbound links | Grep to verify, update frontmatter |
| Template placeholders | `[[{artifact-name}]]`, `[[bare-name]]` | Categorize as non-actionable |
| node_modules content | `[[EventEmitter]]` in plugin source | Exclude from audit scope |
| Git hashes | `[[9403aab]]`, `[[271e02938e5f]]` | Non-actionable, skip |
| Portfolio/external refs | `[[my-portfolio]]` in showcase notes | Non-actionable, skip |

**Broken link audit inflation:** The raw broken-link count includes all of the above. Run a
categorization pass before reporting the "real" broken link count:

```python
# Categorize broken links into actionable vs non-actionable
import re
patterns = {
    'template': r'^\{.*\}$|^bare-name$|^note-name$',
    'hash': r'^[0-9a-f]{7,40}$',
    'external': r'portfolio|showcase',
}
# Count only links not matching any pattern as "real" broken links
```

Expect: a raw count of "137" may reduce to 2-5 genuinely broken concept links.

**Note:** The Python orphan scanner in Step 1 above counts actual wiki-links from file content
and is accurate. This filter applies specifically to *SurrealDB-sourced alerts* (e.g. from
`metabolism/graph-alerts.md`) where metadata staleness is the issue.

### 2. Stub Notes

Find empty template stubs (auto-generated with `{{title}}` placeholders):

```bash
rg -l '\{\{title\}\}|## Problem\s*$|## Solution\s*$' \
  --type md --glob '!.obsidian/**' --glob '!.claude/**' 2>/dev/null
```

Also check for tiny files (< 300B) in content directories:

```bash
find cortex/ cerebellum/ prefrontal/ laboratory/ -name "*.md" -not -name "_*" \
  -size -300c -exec ls -la {} \; 2>/dev/null
```

### 3. Frontmatter Issues

```bash
# Tags as string instead of array (most common issue)
rg -n '^tags: [^[\n]' --type md --glob '!.obsidian/**' --glob '!.claude/**' 2>/dev/null

# Missing title field
rg -L 'title:' cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ 2>/dev/null | head -20

# Missing date field
rg -L 'date:' cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ 2>/dev/null | head -20

# Missing aspect field (required for all content dirs)
rg -L 'aspect:' cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ 2>/dev/null | head -20
```

**Shell check false positive — `head -N` truncation:** Shell-based frontmatter checks that
use `head -20 "$f" | grep -q '^aspect:'` will produce false "missing" counts when notes have
rich frontmatter (neural metadata, dimensions, similar_papers) that pushes `aspect:` past
line 20. The `rg -L '^aspect:'` approach above has the same problem — it searches file content,
not just the frontmatter block, so a body mention of "aspect:" tricks it.

**Use Python for accurate frontmatter-only checks:**

```python
import os, re

for directory in ['sensory', 'prefrontal', 'cortex']:
    missing = []
    for f in os.listdir(directory):
        if not f.endswith('.md') or f.startswith('_'): continue
        path = os.path.join(directory, f)
        with open(path) as fh:
            content = fh.read()
        if not content.startswith('---'): continue
        end_match = re.search(r'\n---', content[3:])
        if not end_match: continue
        frontmatter = content[3:3+end_match.start()]
        if not re.search(r'^aspect:', frontmatter, re.MULTILINE):
            missing.append(f)
    print(f'{directory}: {len(missing)} actually missing aspect')
```

A shell check showing "84 missing" reduced to 0 when checked with Python — all were false
positives from `aspect:` appearing beyond line 20 in valid frontmatter.

### 4. Broken Wiki-Links

```bash
python3 -c "
import os, re

SKIP = ['.obsidian', '.claude', 'node_modules', '.worktrees', '.git', 'tools', 'obsidian-plugin', 'mcp-server']

# Build note name set
note_names = set()
for root, dirs, files in os.walk('.'):
    if any(p in root for p in SKIP):
        continue
    for f in files:
        if f.endswith('.md'):
            note_names.add(f[:-3])

# Find broken links (targets that don't exist)
link_pat = re.compile(r'\[\[([^\]|#]+)')
broken = {}
for root, dirs, files in os.walk('.'):
    if any(p in root for p in SKIP):
        continue
    for f in files:
        if not f.endswith('.md'):
            continue
        path = os.path.join(root, f)
        try:
            with open(path) as fh:
                content = fh.read()
            for m in link_pat.finditer(content):
                target = m.group(1).strip()
                if (target not in note_names
                    and not target.startswith('http')
                    and '/' not in target
                    and target not in ['note-name', 'Note Name', 'note', '...']):
                    broken.setdefault(target, []).append(f[:-3])
        except:
            pass

# Sort by reference count
print('Top broken links (real concept references):')
for target, sources in sorted(broken.items(), key=lambda x: -len(x[1]))[:15]:
    # Skip obvious template artifacts
    if target.lower() in ['note-name', 'note name', 'wiki-link', '...']:
        continue
    print(f'  {target} ({len(sources)} refs): {sources[:3]}')
"
```

**Broken link triage — 88% are non-actionable.** Before investigating individual broken links, bucket them using this fast categorization. In a mature vault (1000+ notes), expect only 10-15% to be truly fixable.

| Category | Detection Pattern | Action | ~% of broken links |
|----------|------------------|--------|-------------------|
| **Template vars** | Contains `{`, `{{`, or generic names like `concept-name`, `note-title`, `paper-slug`, `decision-name`, `lesson-XX` | Ignore — template placeholder | ~55% |
| **Test artifacts** | Pattern `test-\d{10}` (timestamped test outputs) | Ignore — ephemeral test file | ~9% |
| **Git hashes** | `[0-9a-f]{7,40}` | Ignore — commit reference | ~1% |
| **Path-prefixed links in docs** | `dir/slug` format appearing in documentation files explaining the pattern | Ignore — it IS documenting the broken link | ~7% |
| **Path-prefixed links (fixable)** | `[[cortex/foo]]`, `[[motor/bar]]` where `foo.md` exists | Fix: strip directory prefix → `[[foo]]` | ~12% |
| **Case mismatches** | `[[FLUME-architecture]]` vs `[[FLUME-Architecture]]` | Fix: correct case | ~2% |
| **Real missing concepts** | Lowercase-kebab-case, referenced 3+ times, not in any above category | Create stub or fix | ~5% |
| **Portfolio/project-specific** | Proper-noun names like `Cohezion-8-Minute-Demo`, `Agent-Clusters-Anthropic` | Ignore — one-off project reference | ~11% |

**Fast path-prefix fix** (the most common actionable category):
```bash
# Find files with path-prefixed links
grep -rn '\[\[cortex/' . --include="*.md" 2>/dev/null | grep -v '.worktrees/'
# Fix: sed -i 's/\[\[cortex\///g; s/\]\]/]]/g' <files>  — but use Edit tool for safety
```

**Stub creation threshold:** Only create a stub concept note if a broken link is referenced **3+ times** by distinct notes AND is a plausible concept name (lowercase-kebab-case, not a template placeholder). Single-reference broken links are not worth stubbing.

### 5. Thin Notes (Density Gap)

Find low-content notes with high inbound link count (highest-ROI expansion targets):

```bash
python3 -c "
import os, re

SKIP = ['.obsidian', '.claude', 'node_modules', '.worktrees', '.git', 'tools', 'obsidian-plugin', 'mcp-server']

notes = {}
for root, dirs, files in os.walk('.'):
    if any(p in root for p in SKIP):
        continue
    for f in files:
        if f.endswith('.md') and not f.startswith('_'):
            path = os.path.join(root, f)
            notes[f[:-3]] = {'path': path, 'size': os.path.getsize(path), 'inbound': 0}

link_pat = re.compile(r'\[\[([^\]|#]+)')
for name, d in notes.items():
    try:
        with open(d['path']) as fh:
            for m in link_pat.finditer(fh.read()):
                t = m.group(1).strip()
                if t in notes:
                    notes[t]['inbound'] += 1
    except:
        pass

# Thin = < 1500 bytes, has inbound links (prioritize by inbound count)
thin = [(n, d) for n, d in notes.items() if d['size'] < 1500 and d['inbound'] > 2]
thin.sort(key=lambda x: -x[1]['inbound'])
print(f'High-impact thin notes (<1.5KB, 3+ inbound links): {len(thin)}')
for name, d in thin[:10]:
    print(f'  {d[\"inbound\"]:3d} inbound | {d[\"size\"]:4d}B | {name}')
"
```

### 6. Summary Report

Present results in this format:

```markdown
## Vault Health Report — YYYY-MM-DD

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Total notes | X | — | — |
| Wiki-links | X | — | — |
| Thalamus items | X | — | — |
| Orphan notes | X | — | — |
| Stub patterns | X | — | — |
| Frontmatter issues | X | — | — |

### Priority Actions (by impact)
1. [Orphans with context — fix with batch-backlinks skill]
2. [Stubs with ADR rationale — flesh-out from frontmatter data]
3. [Frontmatter issues — vault-frontmatter skill]
4. [Broken real-concept links — create missing cortex notes]
```

## Stub Expansion from ADR Rationale

When cerebellum stubs exist alongside similarly-named prefrontal ADRs, the ADR's frontmatter `decision_reasoning.rationale` field contains the actual knowledge. Extract it into Problem/Solution/When to Use structure:

```
ADR: 2026-03-05-github-issues-as-remote-claude-code-terminal.md
  └── decision_reasoning.rationale: "Zero-latency remote command interface..."
      ↓
Pattern: github-issue-form-as-mobile-claude-terminal.md
  └── Problem: [why SSH/terminal is problematic on mobile]
      Solution: [dropdown Issue Form templates]
      When to Use: [exact scenarios]
```

This is the recovery technique for bulk-generated cerebellum stubs that were created with the right names but empty bodies.

## Thresholds

| Metric | Green | Yellow | Red |
|--------|-------|--------|-----|
| Broken links | < 10 | 10-50 | > 50 |
| Orphan notes | < 5% | 5-15% | > 15% |
| Stubs | < 10 | 10-30 | > 30 |
| Frontmatter issues | 0 | 1-10 | > 10 |

## Notes

- This skill is primarily read-only — it reports issues but does not fix them
- Use other skills (`/link`, `/flesh-out`, `/triage`, `batch-backlinks`) to act on findings
- Python-based orphan scanner runs in ~3 seconds on 1600+ notes (vs. 60+ seconds for shell grep)
- Run after bulk operations to verify vault integrity
- Save results to `hippocampus/YYYY-MM-DD-vault-health.md` for trend tracking
