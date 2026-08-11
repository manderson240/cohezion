---
name: cohezion-ci-debugging
description: CI debugging protocol for the cohezion repo — map failing GitHub checks to their source workflow file FIRST, distinguish workflow-YAML schema errors from step failures, and the ruff --fix / noqa F401 re-export trap. Use when a GitHub Actions check fails, a PR shows a red check, or "workflow file issue" appears.
---

# CI Debugging Protocol (Hard-Won Lessons)

Moved verbatim from root `CLAUDE.md` on 2026-07-17 (doctor context-trim — loads on demand instead of every session).

## Step 1 — Identify the source workflow FIRST

Before reading any logs, map every failing check to its workflow file:
```bash
# Replace RUN_ID with the value from the failing check URL
gh api repos/manderson240/cohezion/actions/runs/$RUN_ID --jq '"\(.name) -> \(.path)"'
```

**Key insight**: The GitHub UI check name ≠ workflow file name. `EnricoMi/publish-unit-test-result-action` creates a check called "Test Results (Python X.Y)" from `ci.yml`. CodeQL creates its own named checks. Fixing the wrong workflow wastes sessions.

## Step 2 — Distinguish workflow-file-issue from step failure

| Signal | Meaning |
|--------|---------|
| `"jobs": []` in API response | Workflow YAML schema error (parse/validate failed) |
| `started_at == completed_at` (0s) | Same — GitHub rejected the file before queuing any runner |
| Job exists but step fails | Normal step failure — read the logs |

**Root cause of "workflow file issue"**: GitHub validates ALL job schemas before evaluating `if:` conditions. A job with `if: false` but no `steps:` still fails validation. `actionlint` pre-commit catches this locally.

```bash
# Quick check: does the failing run have any jobs at all?
gh api repos/manderson240/cohezion/actions/runs/$RUN_ID/jobs --jq '.total_count'
# 0 = schema error in YAML   nonzero = actual step failure
```

## Step 3 — Ruff `--fix` deletes `# noqa: F401` intentional re-exports

Ruff's `--fix` ignores noqa suppression and removes the import anyway. Use `X as X` instead:
```python
# WRONG — ruff --fix will delete this
from cohezion.compound.executor_factory import ExecutorFactory  # noqa: F401

# RIGHT — ruff recognizes same-name alias as public re-export
from cohezion.compound.executor_factory import ExecutorFactory as ExecutorFactory
```
