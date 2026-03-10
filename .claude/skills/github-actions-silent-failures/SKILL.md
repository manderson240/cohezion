---
name: github-actions-silent-failure-patterns
description: |
  Detect and fix GitHub Actions / pre-commit configurations that silently do nothing instead of failing.
  Use when: (1) code review finds suspicious CI configs, (2) security gates feel ineffective,
  (3) pre-commit hooks always pass even when they should fail,
  (4) GitHub Actions search queries return empty results.
  Key patterns: sys.exit(print()), no:label+label: mutual exclusion,
  continue-on-error on security gates, wrong workflow_name in reusable workflows.
author: Claude Code
version: 1.0.0
---

# GitHub Actions Silent Failure Patterns

## Problem

GitHub Actions workflows and pre-commit hooks can be silently broken — they run without errors
but never actually block anything. These bugs are invisible in CI logs and easy to miss in code
review because the syntax is valid.

## Pattern 1: sys.exit(print()) Always Exits 0

**The bug:** Python's `print()` returns `None`. So `sys.exit(print("error"))` is
`sys.exit(None)` which exits with code 0 (success). The hook always passes.

```yaml
# BAD - always exits 0, never blocks commits
- id: large-artifact-gate
  entry: python -c "import sys,os;[sys.exit(print(f'ERROR: {f} exceeds 50MB')) for f in sys.argv[1:] if os.path.getsize(f)>52428800]"
```

**Fix:** Use `sys.exit(1)` to signal failure, print separately if needed.

```yaml
# GOOD - actually fails when large files detected
- id: large-artifact-gate
  entry: python -c "import sys,os;bad=[f for f in sys.argv[1:] if os.path.getsize(f)>52428800];[print(f'ERROR: {f} exceeds 50MB') for f in bad];sys.exit(1 if bad else 0)"
```

Or extract to a script file (cleaner, easier to test):
```python
# scripts/hooks/check_artifact_size.py
import sys, os
bad = [f for f in sys.argv[1:] if os.path.getsize(f) > 52_428_800]
for f in bad:
    print(f"ERROR: {f} exceeds 50 MB limit — register as external artifact")
sys.exit(1 if bad else 0)
```

**Diagnosis:** Run the hook manually with a large file:
```bash
python -c "import sys,os;[sys.exit(print(f'big: {f}')) for f in sys.argv[1:] if os.path.getsize(f)>52428800]" /tmp/bigfile.bin
echo "Exit code: $?"  # Should be 1, but is 0 with the bug
```

## Pattern 2: no:label AND label: Mutual Exclusion in GitHub Search

**The bug:** `no:label` means "issues with no labels". `label:"status/needs-triage"` means
"issues with this specific label". These filters contradict each other — the result is always empty.

```yaml
# BAD - query returns 0 results, triage bot never runs
- name: Get untriaged issues
  uses: actions/github-script@v7
  with:
    script: |
      const issues = await github.search.issuesAndPullRequests({
        q: 'repo:${{ github.repository }} is:open is:issue no:label label:"status/needs-triage"'
      });
```

**Fix:** Pick one filter. To find truly unlabeled issues, use `no:label` alone:

```yaml
# Find issues with NO labels at all
q: 'repo:${{ github.repository }} is:open is:issue no:label'

# OR find issues specifically labeled "needs-triage"
q: 'repo:${{ github.repository }} is:open is:issue label:"status/needs-triage"'
```

**Diagnosis:** Run the search query in GitHub's search bar and verify it returns results.

## Pattern 3: continue-on-error Negating Security Gates

**The bug:** Setting `continue-on-error: true` on a security-critical step means the step's
failure is recorded as a "warning" but the job continues and succeeds. This makes the security
gate decorative.

```yaml
# BAD - dependency review failure is silently ignored
- name: Dependency Review
  uses: actions/dependency-review-action@v4
  continue-on-error: true  # This defeats the entire purpose
```

**Fix:** Remove `continue-on-error: true` from security gate steps. If you need the job to
continue despite failures in other steps, use `if: always()` on subsequent steps instead.

```yaml
# GOOD - dependency review actually blocks the PR
- name: Dependency Review
  uses: actions/dependency-review-action@v4
  # No continue-on-error — failures must block
```

**Acceptable uses of continue-on-error:** Non-security informational steps like coverage
reporting, optional notifications, or diagnostics that shouldn't block CI.

## Pattern 4: Wrong workflow_name in Reusable Workflow Dispatch

**The bug:** When using `workflow_dispatch` with `workflow_name:` to target a reusable workflow,
the name must exactly match the `name:` field in the target workflow YAML, not the filename.

```yaml
# BAD - references filename, not the workflow's name: field
- uses: actions/github-script@v7
  with:
    script: |
      github.actions.createWorkflowDispatch({
        workflow_id: 'gemini-invoke.yml',
        // workflow_name: 'gemini-invoke'  ← wrong if the workflow's name: field differs
      })
```

```yaml
# gemini-invoke.yml target workflow
name: "Gemini AI Invocation"  # This is the name to use, not the filename
```

**Fix:** Check the `name:` field at the top of the target workflow file:

```bash
grep "^name:" .github/workflows/gemini-invoke.yml
# name: "Gemini AI Invocation"
```

Then use that exact string in `workflow_name:`.

## Verification Checklist for CI Code Reviews

When reviewing GitHub Actions workflows, check:

- [ ] Pre-commit hook entries: does `sys.exit()` receive `1` (not `print()` or `None`)?
- [ ] GitHub search queries: are `no:label` and `label:X` used together? (always returns 0 results)
- [ ] Security gate steps: do they have `continue-on-error: true`? (removes blocking behavior)
- [ ] Reusable workflow dispatches: does `workflow_name` match the `name:` field, not the filename?
- [ ] Any step exit code that determines blocking: verify it actually returns non-zero on failure

## References

- Python `sys.exit()` docs: `None` is treated as 0 (success)
- GitHub Issues search syntax: https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests
- `continue-on-error`: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/using-jobs-in-a-workflow
