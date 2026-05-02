---
title: Syntax Rules
description: Critical syntax patterns for Cohezion Python codebase
created: 2026-03-08
traced_from:
  - source: AGENTS.md
    section: Code Style Guidelines
    commit: d2f7129f
  - source: AGENTS.md
    section: Async/Await
    commit: d2f7129f
coherence_threshold: 0.5
---

# Core Syntax Rules

## Python 3.13+ Standards
- **Line Length**: 100 characters maximum
- **Package Manager**: `uv` (never bare pip)
- **Type Hints**: Mandatory, mypy --strict compatible
- **Docstrings**: NumPy-style (intent and assumptions, not mechanics)

## Import Order (Critical)
1. `from __future__ import annotations`
2. Standard library (alphabetical)
3. Third-party packages
4. Local imports (`cohezion`)

## Async/Await (Non-Negotiable)
All I/O must be async with timeouts. No blocking calls in executors.

**Correct:**
```python
async def fetch_data(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await client.get(url)
```

**Wrong:**
```python
def fetch_data(url: str) -> dict[str, Any]:
    return requests.get(url).json()  # Blocking!
```

## FUTURE HOOKS
1. **Auto-format on save**: Future IDE integration will auto-apply these rules
2. **Import linting**: Future pre-commit hooks will enforce import order
3. **Async detection**: Future static analysis will flag blocking calls
