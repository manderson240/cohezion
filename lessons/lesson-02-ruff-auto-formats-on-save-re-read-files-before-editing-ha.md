---
title: Ruff Auto-Formats on Save: Re-Read Files Before Editing
date: 2026-02-23
severity: MEDIUM
category: tooling
tags: [ruff, formatting, pre-commit, file-editing]
status: validated
---

# Lesson: Ruff Auto-Formats on Save: Re-Read Files Before Editing

## Context

Ruff is configured to auto-format Python files on save. When Claude Code reads a file and then edits it after any save has occurred, the file may have been reformatted, causing edit conflicts or stale-offset errors.

## Core Learning

**Always re-read a file immediately before editing if any time has passed or any save/format action may have occurred.**

### Why This Matters
- Ruff may reformat on any save trigger, changing whitespace and import order
- Edit tools match on exact string content -- stale reads cause mismatches
- Silent failures (wrong line edited) are hard to debug

### Pattern
```
WRONG: read once, edit later
  content = read("src/foo.py")
  ... do other things ...
  edit("src/foo.py", old_string, new_string)  # May fail -- file changed

RIGHT: read immediately before edit
  content = read("src/foo.py")  # fresh read
  edit("src/foo.py", old_string, new_string)  # guaranteed current
```

## Recommendations

### Do
- Re-read files immediately before any Edit operation
- Treat reads and edits as an atomic pair

### Don't
- Cache file reads for reuse across multiple unrelated edits
- Assume file content is stable across tool calls

## Related Concepts

- [[compound-engineering]] - Edit correctness is foundational to compound workflows

## Validation

**Discovered**: Feb 2026
**Status**: Validated in Python development sessions
