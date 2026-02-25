---
title: Sequential Numbering Offset Corrupts Indexes
date: 2026-02-24
severity: medium
category: vault-integrity
tags: [lesson, vault, indexing, numbering, lessons-index]
status: active
---

# Lesson 40: Sequential Numbering Offset Corrupts Indexes

## Core Learning

Auto-generated lesson indexes that use sequential numbering (lesson-118 through lesson-155) will break if the underlying files use semantic IDs (lesson-01 through lesson-38). When lesson files are re-created with a different numbering scheme, all existing index references become dead links. Semantic IDs are resilient; sequential offsets are fragile.

## The Problem

The auto-generated `patterns/lessons/_lessons_index.md` assigned sequential IDs starting from 118 (the file was previously part of a larger lessons corpus and numbered from where that corpus left off). When 38 new lesson files were created using `lesson-01` through `lesson-38` IDs, the index still referenced `lesson-118` through `lesson-155` — every single entry was a dead link.

Additionally, the "Quick Navigation" section of the same index used a **different** offset scheme (lesson-03 through lesson-24 with CAPS names like `lesson-03-SURGERY-LESSON`) — creating two misaligned numbering systems in the same file.

## The Fix

Completely rewrote `_lessons_index.md` with the correct semantic IDs:
```markdown
- [[lesson-01-agent-has-great-content-but-claude-code-only-auto-reads]]
- [[lesson-02-ruff-auto-formats-on-save-re-read-files-before-editing-ha]]
...
```

## Prevention

- **Use semantic IDs**, not sequential: `lesson-surgery-lesson` not `lesson-04`
- **Test generated indexes** — add a vault test that verifies all index links resolve
- **Never use global sequence counters** across corpus boundaries — the counter resets but the IDs don't change

## Do / Don't

✅ Semantic IDs: `lesson-surgery-lesson`, `lesson-yaml-folded-scalar-trap`
✅ Test that generated indexes have 0 broken links
❌ Sequential offsets from prior corpus counts (lesson-118 when files start at lesson-01)
❌ Two different numbering schemes in the same index (All Lessons vs. Quick Nav)

## Related

- [[patterns/lessons/_lessons_index.md]]
- [[2026-02-24-vault-link-integrity-sprint]]
- [[lesson-39-vault-audit-must-exclude-worktrees]]
