---
title: Gitignore Ordering: Later Rules Override Earlier Rules for the Same Path
date: 2026-02-23
severity: MEDIUM
category: git
cost_of_forgetting: "Files tracked or ignored unexpectedly due to rule ordering; potential for large files entering git history"
tags: [git, gitignore, configuration, file-management]
status: validated
aspect: knower
neural:
  activation: 0.430
  stage: growing
  cluster: lessons
---

# Lesson: Gitignore Ordering: Later Rules Override Earlier Rules for the Same Path

## Context

During the large repository cleanup in February 2026 (related to [[lesson-13-8-6m-file-incident]]), investigation revealed that some files that should have been ignored were being tracked, and vice versa. The `.gitignore` file had grown organically with contributions from multiple sessions, and the rule ordering had become non-obvious. A negation pattern (`!important_data.jsonl`) near the bottom of the file was un-ignoring a file that a broad pattern (`*.jsonl`) near the top was supposed to ignore.

## Problem

Git processes `.gitignore` rules sequentially, with later rules overriding earlier rules for the same path. This last-rule-wins behavior creates subtle bugs:

1. **Accidental un-ignore**: A `!file.ext` negation pattern later in the file overrides a `*.ext` ignore pattern earlier
2. **Shadow rules**: A specific ignore pattern is added without realizing a broader pattern above already covers it (harmless but confusing)
3. **Debug difficulty**: When a file is unexpectedly tracked or ignored, developers grep the `.gitignore` for matching patterns but may not account for ordering

Without using `git check-ignore -v`, the effective rule for any given path is ambiguous.

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

## Solution

The `.gitignore` was reorganized with explicit sections and ordering discipline:

1. **Broad patterns at the top**: `*.jsonl`, `*.parquet`, `venv/`, `data/`
2. **Specific patterns in the middle**: `src/generated/`, `.claude/3d-graph-data.json`
3. **Negation patterns at the bottom** (if any): `!.env.example`

For any uncertain path, `git check-ignore -v <path>` is the definitive debugging tool.

## Prevention

- **Use `git check-ignore -v` to verify**: Before assuming a file is ignored, check which rule applies
- **Organize `.gitignore` top-down**: Broad to specific, with negations last
- **Minimize negation patterns**: Each negation is a potential confusion source
- **Review `.gitignore` changes in PRs**: Rule ordering changes can have non-obvious effects

## Cost of Forgetting

- **Unexpected file tracking**: Files that should be ignored enter git history (see [[lesson-13-8-6m-file-incident]])
- **Unexpected file ignoring**: Files that should be tracked are silently excluded
- **Debugging time**: Minutes to hours spent figuring out why a file is or is not in git

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
- [[data-governance-prevention-through-pre-commit-enforcement]] - gitignore is the first line of data governance defense
- [[data-discipline-prevent-generated-data-in-git]] - gitignore ordering directly affects whether generated data is properly excluded

## Validation

**Discovered**: Feb 2026 during large repository cleanup
**Status**: Validated -- .gitignore reorganized with documented ordering
