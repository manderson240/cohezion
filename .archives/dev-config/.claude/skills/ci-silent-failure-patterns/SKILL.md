---
name: ci-silent-failure-patterns
description: |
  Patterns that make CI/CD security gates and pre-commit hooks silently pass when they should fail.
  Use when: (1) reviewing CI workflows or pre-commit configs for correctness,
  (2) a security gate exists but you suspect it's not actually blocking anything,
  (3) pre-commit hooks print errors but don't block commits.
  Key patterns: `continue-on-error: true` negates `fail-on-severity`, `sys.exit(print(...))` always exits 0.
author: Claude Code
version: 1.0.0
---

# CI Silent Failure Patterns

## Problem

CI security gates and pre-commit hooks can appear to work while silently passing everything through. These patterns look like enforcement but have no effect.

## Pattern 1: `continue-on-error: true` Negates Security Gates (GitHub Actions)

### Symptom

A GitHub Actions step has both a security-enforcing config (`fail-on-severity: high`, `--exit-code 1`, etc.) AND `continue-on-error: true`.

### Why It Fails

`continue-on-error: true` intercepts the step's non-zero exit code and marks it as "neutral" rather than "failure". The workflow continues and any required status checks pass. The security gate is completely disabled.

```yaml
# BROKEN — continue-on-error negates fail-on-severity
- name: Dependency Review
  uses: actions/dependency-review-action@v3
  with:
    continue-on-error: true        # ← this line defeats the entire point
    fail-on-severity: high
    comment-summary-in-pr: on-failure
```

```yaml
# CORRECT — let the action fail the workflow
- name: Dependency Review
  uses: actions/dependency-review-action@v3
  with:
    fail-on-severity: high
    comment-summary-in-pr: on-failure
```

### When to Use `continue-on-error`

Only when you genuinely want the workflow to succeed regardless of the step's result (e.g., optional informational steps). Never on security gates.

---

## Pattern 2: `sys.exit(print(...))` Always Exits 0 (Pre-commit Hooks)

### Symptom

A pre-commit hook's `entry` uses a Python one-liner like:
```yaml
entry: python -c "import sys,os;[sys.exit(print(f'ERROR: {f}')) for f in sys.argv[1:] if condition]"
```

The hook prints the error message but the commit proceeds anyway.

### Why It Fails

`print()` always returns `None`. Therefore `sys.exit(None)` exits with code **0** (success). The hook signals success to pre-commit, which allows the commit.

```python
# This looks like it blocks, but it doesn't:
sys.exit(print("ERROR: file too large"))
# Equivalent to:
print("ERROR: file too large")  # returns None
sys.exit(None)                   # exit code 0 = success!
```

### Fix

Separate the print and exit calls:

```yaml
# BROKEN
entry: python -c "import sys,os;[sys.exit(print(f'ERROR {f}')) for f in sys.argv[1:] if os.path.getsize(f)>52428800] or None"

# CORRECT — exit with code 1 explicitly
entry: python -c "
import sys, os
bad = [f for f in sys.argv[1:] if os.path.getsize(f) > 52428800]
if bad:
    for f in bad:
        print(f'ERROR: {f} ({os.path.getsize(f)//1048576}MB) exceeds 50MB limit')
    sys.exit(1)
"
```

Or use a separate script file for clarity.

---

## Pattern 3: Mutually Exclusive GitHub Search Filters

### Symptom

A `gh issue list --search` or `gh api` call with filters that can never both be true simultaneously returns empty results, and automated workflows silently do nothing.

### Example

```bash
# BROKEN — no:label and label:X are mutually exclusive
gh issue list --search 'no:label label:"status/needs-triage"'
# Returns: [] always

# CORRECT — separate searches or use OR
gh issue list --search 'no:label'
gh issue list --search 'label:"status/needs-triage"'
```

`no:label` = issue has zero labels. `label:"X"` = issue has label X. Both cannot be true. GitHub ANDs multiple qualifiers by default.

---

## Code Review Checklist

When reviewing CI workflows and pre-commit configs, check for:

- [ ] Any step with `continue-on-error: true` that is supposed to be a gate
- [ ] Any `sys.exit()` call that wraps `print()` directly
- [ ] Any search query using `no:label` combined with `label:` qualifiers
- [ ] Any step that uses `|| true` or `; true` to suppress failures in security contexts

## Verification

To confirm a pre-commit hook actually blocks:

```bash
# Create a test file exceeding the limit
dd if=/dev/zero of=test_large.bin bs=1M count=55

# Stage it and verify the hook blocks
git add test_large.bin
git commit -m "test" --no-verify  # skip hooks first
git reset HEAD~1                   # undo
git add test_large.bin
git commit -m "test"               # should fail with the hook

# Clean up
rm test_large.bin
git restore --staged test_large.bin 2>/dev/null || true
```

## References

- GitHub Actions `continue-on-error`: https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#jobsjob_idstepscontinue-on-error
- Python `sys.exit(None)` is exit code 0: https://docs.python.org/3/library/sys.html#sys.exit
- GitHub issue search syntax: https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests
