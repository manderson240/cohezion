---
title: Vault Link Audit Pattern
date: 2026-02-24
tags: [pattern, vault, links, obsidian, audit]
aspect: thinker
neural:
  activation: 0.84
  stage: growing
  synapse_in: 6
  synapse_out: 22
---

# Vault Link Audit Pattern

## Problem

Obsidian wiki-links silently break when files are renamed, moved, or never created. Large vaults (500+ notes) accumulate hundreds of broken links over time, fragmenting the knowledge graph and making navigation unreliable.

## Solution

Run a multi-pass audit script that classifies broken links by type and applies targeted fixes for each class.

## Audit Script

```python
import re
from pathlib import Path

vault = Path(".")
SKIP = {'.worktrees', '.git', '.obsidian', 'node_modules', 'tools'}

all_md = [
    f for f in vault.rglob("*.md")
    if not any(part in SKIP for part in f.parts)
]
all_stems = {f.stem.lower(): f.stem for f in all_md}
link_re = re.compile(r'\[\[([^\]|#\n]+?)(?:\|[^\]]+)?\]\]')

broken = {}
for f in all_md:
    content = f.read_text(errors='replace')
    for m in link_re.finditer(content):
        target = m.group(1).strip()
        if target.lower() not in all_stems:
            broken.setdefault(target, []).append(str(f))

print(f"Broken targets: {len(broken)}")
for target, files in sorted(broken.items(), key=lambda x: -len(x[1])):
    print(f"  {len(files)}x [[{target}]]")
```

## Fix Passes (Apply in Order)

### Pass 1: Case and Slug Corrections
Map `[[Compound Engineering]]` → `[[compound-engineering]]` using a rewrite dict.

### Pass 2: Strip Directory Path Prefixes
`[[cerebellum/runbook-health-checks]]` → `[[runbook-health-checks]]` when the stem exists.

### Pass 3: Space-to-Hyphen Normalization
`[[agent context]]` → `[[agent-context]]` — Obsidian resolves by filename stem, not space-separated words.

### Pass 4: Create Stubs for Genuinely Missing Content
For high-value broken links with no plausible rewrite, create stub notes with proper frontmatter.

### Pass 5: Fix .md-Suffix and Date-Prefix Mismatches
`[[prefrontal/2026-02-11-use-surrealdb.md]]` → strip `.md` and path prefix.

### Pass 6: Fix Generated Index Numbering
Auto-generated indexes may use offset sequential IDs. Rewrite to match actual file stems.

## Skippable Link Classes

Not all broken links need fixing. Skip these:
- `[[_PRIME]]` links in `skills_index.md` — external skill file identifiers
- `[[{template_var}]]` and `[[{{mustache}}]]` — template placeholders
- `[[file.py]]`, `[[file.ts]]` — source code references
- `[[9403aab]]` — git hashes
- `[[concept1]]`, `[[paper-slug]]` — template example placeholders
- Section-header pseudo-links: `[[Queries]]`, `[[Scenarios]]`

## When to Run

- After bulk note creation or migration
- After renaming/moving note directories
- Before publishing or sharing vault content
- As a CI check (see vault test suite)

## Expected Outcome

In a 906-note vault starting with 728 broken targets:
- After 6-8 passes: ~167 broken targets remaining (all legitimately non-fixable)
- Tag format: 0 violations
- Missing frontmatter: 0 notes

## Related

- [[lesson-39-vault-audit-must-exclude-worktrees]]
- [[lesson-40-sequential-numbering-offset-corrupts-indexes]]
- [[2026-02-24-vault-link-integrity-sprint]]
- [[2026-02-24-vault-link-integrity-first-principle]] — the decision that establishes vault link integrity as a first-class engineering concern
