---
title: Gitignore Ordering: Later Rules Override Earlier Rules for the Same Path
date: 2026-02-23
severity: MEDIUM
category: git
tags: [git, gitignore, configuration, file-management]
status: validated
---

# Lesson: Gitignore Ordering: Later Rules Override Earlier Rules for the Same Path

## Context

Gitignore rules are processed in order -- later rules override earlier rules for the same path. A negation pattern at the bottom can un-ignore something blocked at the top.

## Core Learning

**Gitignore is last-rule-wins for a given path. Verify the effective rule for any path with git check-ignore -v <path>.**

### Pattern
```bash
# Check effective gitignore rule for a path
git check-ignore -v venv/
# Output: .gitignore:5:venv/  venv/ is ignored by rule at line 5

# Check why a file IS tracked (not ignored)
git check-ignore -v src/important_file.py
# No output = file is not ignored by any rule
```

## Recommendations

### Do
- Use git check-ignore -v <path> to debug unexpected tracking behavior
- Put broad ignore patterns (venv/, data/) at the TOP of .gitignore
- Use negation patterns sparingly and always at the end

### Don't
- Mix broad and narrow rules without understanding ordering
- Assume a file is ignored because it matches a pattern

## Related Concepts

- [[lesson-13-8-6m-file-incident]] - Large file committed due to missing gitignore rule

## Validation

**Discovered**: Feb 2026 during large repository cleanup
**Status**: Validated
