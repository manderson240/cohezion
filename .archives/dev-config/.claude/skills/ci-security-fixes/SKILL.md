---
name: ci-security-fixes
description: |
  Fix CI failures from CodeQL security alerts and GitHub Actions workflow issues.
  Use when: (1) CodeQL reports path traversal, log injection, or command injection,
  (2) GitHub Actions workflows fail due to missing directories/lockfiles,
  (3) Tests fail in CI due to kernel capabilities (OverlayFS, Docker).
author: Claude Code
version: 1.0.0
---

# CI Security & Workflow Fix Patterns

## Problem

CodeQL security alerts and GitHub Actions environment mismatches cause CI failures.

## Pattern 1: Centralized Security Utility (safe_input.py)

When CodeQL reports path traversal or log injection across multiple files, create a shared utility:

```python
# src/your_project/servers/safe_input.py
import re
from pathlib import Path

def sanitize_path(user_path: str, base_dir: str | Path | None = None) -> Path:
    resolved = Path(user_path).resolve()
    if base_dir is not None:
        base = Path(base_dir).resolve()
        try:
            resolved.relative_to(base)
        except ValueError:
            raise ValueError(f"Path escapes allowed directory: {user_path}") from None
    return resolved

def sanitize_log(value: str) -> str:
    return re.sub(r"[\r\n\x00-\x1f\x7f]", " ", str(value))
```

Apply across all affected files in one commit rather than fixing each independently.

## Pattern 2: Workflow Path Filters

When workflows reference directories not committed to git:

```yaml
on:
  pull_request:
    paths:
      - 'src/web/dashboard/**'  # Only trigger when directory changes
```

Add existence check as defense-in-depth:

```yaml
- name: Check exists
  id: check
  run: test -f path/to/package.json
  continue-on-error: true
- name: Next step
  if: steps.check.outcome == 'success'
```

## Pattern 3: npm ci vs npm install

`npm ci` requires a committed lockfile. Use `npm install --no-audit --no-fund` when no lockfile exists.

## Pattern 4: CI Environment Skip Markers

For tests requiring kernel capabilities (OverlayFS, Docker):

```python
import os
pytestmark = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="OverlayFS not available in CI containers",
)
```

## Pattern 5: stderr Corrupting JSON Output

Never use `2>&1` when capturing structured output. Use `2>/dev/null` or redirect stderr separately.

## Verification

After fixes, check all CI passes:
```bash
gh pr checks <PR_NUMBER>
```
