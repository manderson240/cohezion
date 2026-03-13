---
title: Ruff Auto-Formats on Save: Re-Read Files Before Editing
date: 2026-02-23
severity: MEDIUM
category: tooling
cost_of_forgetting: "Edit tool failures from stale file content; silent mismatches when wrong line is edited"
tags: [ruff, formatting, pre-commit, file-editing]
status: validated
aspect: knower
neural:
  activation: 0.69
  stage: growing
  synapse_in: 6
  synapse_out: 4
---

# Lesson: Ruff Auto-Formats on Save: Re-Read Files Before Editing

## Context

During Cohezion Python development sessions in February 2026, the Edit tool began failing intermittently with "old_string not found" errors. The target string existed in the file moments before, but by the time the Edit tool executed, the file content had changed. Investigation revealed that ruff (configured as a save-on-format hook in the IDE and as a pre-commit hook) was reformatting files between the Read and Edit operations.

## Problem

The failure chain works as follows:

1. Claude Code reads `src/foo.py` and sees the current content
2. Another operation occurs (another file save, a pre-commit hook run, or IDE auto-save)
3. Ruff reformats `src/foo.py` -- changing whitespace, import ordering, or line wrapping
4. Claude Code attempts an Edit using the old content as `old_string` -- the match fails because the file has been reformatted
5. In the worst case, the edit succeeds on a different location in the file where the `old_string` still matches, creating a silent corruption

The time window between read and edit can be as short as a few seconds, but ruff runs in milliseconds on save.

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

## Solution

The operational discipline is simple: treat Read and Edit as an atomic pair. Never allow intervening operations between reading a file and editing it. This was encoded in the coding standards rules and is now a mandatory practice for all agent sessions.

## Prevention

- **Atomic read-edit pairs**: Always re-read immediately before editing
- **Minimize time between read and edit**: Do not perform other file operations or tool calls between them
- **Verify edit success**: After editing, check that the expected change was applied (the Edit tool returns success/failure)
- **Be aware of formatting hooks**: Know which files have auto-format configured (ruff for Python, prettier for JS/TS)

## Cost of Forgetting

- **Edit tool failures**: "old_string not found" errors that require re-reading and retrying
- **Silent mismatches**: Edits applied to wrong locations in the file
- **Debugging difficulty**: The error is in the stale read, but symptoms appear in the edit

## Recommendations

### Do
- Re-read files immediately before any Edit operation
- Treat reads and edits as an atomic pair

### Don't
- Cache file reads for reuse across multiple unrelated edits
- Assume file content is stable across tool calls

## Related Concepts

- [[compound-engineering]] - Edit correctness is foundational to compound workflows
- [[lesson-09-ruff-hook-fights]] - Related: ruff hook configuration issues with auto-fix and re-staging
- [[concept-automation]] - Auto-formatting hooks create an implicit concurrent modification of files
- [[lesson-16-pre-commit-hooks-stage-override]] - Pre-commit hooks modify files as a side effect, same class of problem

## Validation

**Discovered**: Feb 2026 in Python development sessions
**Status**: Validated -- now encoded in coding standards
