---
title: "Sanitize environment variable path components"
date: "2026-02-22"
tags: [pattern, security, python]
aspect: thinker
neural:
  activation: 0.63
  stage: growing
  synapse_in: 4
  synapse_out: 7
---

## Problem

Environment variables used as filesystem path components (e.g. session IDs, user-supplied directory names) can contain path traversal sequences like `../../etc`, allowing an attacker to escape the intended directory.

## Solution

Strip any character that isn't safe for a path component before constructing the path. Use a compiled regex for clarity and reuse.

## Code Example

```python
import re

_SAFE_RE = re.compile(r"[^a-zA-Z0-9_\-]")

def sanitize_path_component(value: str) -> str:
    """Replace unsafe characters with underscores."""
    return _SAFE_RE.sub("_", value)

# Usage
session_id = sanitize_path_component(os.environ.get("SESSION_ID") or "default")
session_dir = base_dir / session_id  # safe
```

Real-world example from `cohezion_engine/session.py`:

```python
_SESSION_ID_RE = re.compile(r"[^a-zA-Z0-9_\-]")

def get_session_id() -> str:
    raw = os.environ.get("COHEZION_SESSION_ID") or f"pid-{os.getpid()}"
    return _SESSION_ID_RE.sub("_", raw)
```

## When to Use

- Any time an environment variable, user input, or external value is used as a directory or file name
- Session IDs, user slugs, tenant identifiers, upload filenames
- Before constructing paths with `pathlib` or `os.path.join`

**Do not use** `os.path.basename` as a substitute — it strips leading separators but not embedded traversal sequences like `foo/../../etc`.

## Related Decisions

- [[2026-02-22-security-fixes-session-id-path-traversal-and-github-date]] — real-world application: COHEZION_SESSION_ID path traversal fix in cohezion-engine
- [[2026-02-19-block-destructive-system-operations-from-ai-tools]] — broader security posture within which path sanitization fits

## Related Patterns

- [[service-initialization-checklist]] — path sanitization should be part of service initialization when session directories are created
- [[platform-issue-analysis-template]] — path traversal vulnerabilities are discoverable through systematic platform issue analysis

## Related Concepts

- [[ai-safety]] — path sanitization is a concrete AI safety practice preventing agents from escaping intended directories
- [[context-management]] — session IDs constructed from environment variables are context artifacts that must be sanitized before filesystem use
- [[concept-testing]] — validating that sanitized path components never produce traversal sequences is a form of concept correctness testing
