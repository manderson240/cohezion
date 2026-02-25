---
title: Vault Link Integrity Sprint — 906-Note Full Audit
date: 2026-02-24
status: complete
tags: [experiment, vault, links, integrity, obsidian]
---

# Vault Link Integrity Sprint — 906-Note Full Audit

## Hypothesis

A full multi-pass audit and repair of the 906-note vault would resolve the majority of broken wiki-links and produce a traversable, bidirectionally-linked knowledge graph.

## Method

Six sequential fix passes over two sessions, each targeting a distinct class of broken link:

| Pass | Type | Count Fixed |
|------|------|------------|
| 1 | Case/slug corrections (`Compound Engineering` → `compound-engineering`) | 20 targets |
| 2 | Strip directory path prefixes (`[[patterns/foo]]` → `[[foo]]`) | 28 targets |
| 3 | Space-to-hyphen normalization (`[[agent context]]` → `[[agent-context]]`) | ~30 targets |
| 4 | Create 54 stub notes for genuinely missing content | 54 stubs |
| 5 | `.md` suffix strip + date-prefix corrections | 15 targets |
| 6 | CAPS/underscore/sentence-fragment mass rewrite | 74 targets |
| 7 | Lesson index sequential numbering rewrite (118→155 corrected to 01→38) | 38 targets |
| 8 | Retrospectives path-prefix strip + final stubs | 12 targets |

**Supporting fixes (non-link):**
- 77 notes: block-style tags → inline array YAML
- 59 notes: missing frontmatter added
- 40 lesson files created (`lesson-01` through `lesson-38`)

## Results

| Metric | Before | After |
|--------|--------|-------|
| Vault notes | 499 (non-recursive audit) | 906 (recursive, excluding worktrees) |
| Broken link targets | ~728 | ~167 |
| Broken instances | ~3,905 (with worktrees) | 307 (main vault only) |
| Tag format violations | 77 | 0 |
| Missing frontmatter | 59 | 0 |
| Lesson files | 3 | 45 |

**Remaining 167 broken targets are all non-fixable by design:**
- `_PRIME` skill references in `skills_index.md` (external skill files, not vault notes)
- `.py`/`.ts` source file references (code paths, not notes)
- Git hash links (`[[9403aab]]`)
- Template placeholders (`{{note_path}}`, `concept1`, etc.)
- Section-header pseudo-links (`[[Queries]]`, `[[Scenarios]]`)

## Learnings

1. **Worktrees inflate broken link counts by 3-5x** — always exclude `.worktrees/` before auditing
2. **Non-recursive glob misses entire subdirectories** — `concepts/cs249r/` (22 files) was invisible until `rglob()` used
3. **Auto-generated indexes inherit offset numbering** — lesson index used 118-155 instead of 01-38
4. **Template placeholders are indistinguishable from real broken links** without examining source context
5. **`skills_index.md` PRIME references** are skill file identifiers, not vault notes — don't try to create stubs for them
6. **Multi-pass is essential** — each pass reveals a new class of breakage not visible in prior passes

## Related

- [[vault-link-audit-pattern]]
- [[lesson-39-vault-audit-must-exclude-worktrees]]
- [[lesson-40-sequential-numbering-offset-corrupts-indexes]]
- [[2026-02-24-vault-link-integrity-first-principle]]
