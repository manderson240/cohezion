---
title: "Safe File Split Checklist"
date: "2026-02-17"
tags: [pattern, refactoring, checklist, python]
aspect: thinker
neural:
  activation: 0.7
  stage: growing
  synapse_in: 6
  synapse_out: 7
---

# Safe File Split Checklist

## Problem

When a Python module grows beyond 300 lines (or 500 lines as a hard limit), it must be split into focused sub-modules. File splits are one of the most error-prone refactoring operations because they change import paths, move class/function definitions, and can silently break callers that reference the old location. Common failures include:

1. **Duplicate singletons** — both the original and new file contain the singleton class, creating two independent instances
2. **Broken imports** — callers still import from the old module path
3. **Orphan modules** — the new file is created but never wired into the package's `__init__.py`
4. **Missed callers** — internal callers within the same file or test files still reference the old location
5. **Lost re-exports** — the original module no longer re-exports symbols that downstream code depends on

## Solution

Follow this **mandatory checklist** for every file split operation:

### Pre-Split

- [ ] **Identify all symbols being moved** — classes, functions, constants, type aliases
- [ ] **Identify all singletons** — grep for `_instance`, `__new__`, `@classmethod` patterns
- [ ] **Map all callers** — `grep -rn "from old_module import" src/ tests/` and `grep -rn "old_module\." src/ tests/`
- [ ] **Choose canonical homes** — decide which module owns each symbol

### During Split

- [ ] **Move symbols to new module** — cut from old, paste to new
- [ ] **Singleton consolidation** — each singleton lives in exactly ONE module ([[2026-02-17-singleton-consolidation-mandatory-during-file-splits]])
- [ ] **Update `__init__.py`** — re-export moved symbols from the package for backward compatibility
- [ ] **Update all callers** — change import paths in all files identified in pre-split
- [ ] **Update conftest.py** — singleton reset fixtures must reference the new canonical import path

### Post-Split Verification

- [ ] **No duplicate definitions** — `grep -rn "class ClassName" src/` returns exactly ONE result per class
- [ ] **No orphan modules** — every new `.py` file is imported by at least one other file
- [ ] **All tests pass** — `uv run pytest` with full suite (not just individual test files)
- [ ] **No import errors** — `python -c "import package.new_module"` succeeds
- [ ] **File sizes** — both resulting files are under 300 lines

## Code Example

Splitting `big_module.py` (450 lines) into `core.py` and `helpers.py`:

```bash
# Pre-split: Map all callers
grep -rn "from big_module import" src/ tests/
grep -rn "big_module\." src/ tests/

# Pre-split: Check for singletons
grep -rn "_instance" src/big_module.py

# Post-split: Verify no duplicates
grep -rn "class MyService" src/  # Must return exactly 1 result

# Post-split: Verify no orphans
grep -rn "import helpers" src/   # Must return at least 1 result

# Post-split: Verify backward compatibility
python -c "from package.big_module import MyService"  # Should still work via __init__.py re-export
```

## When to Use

- **Any file exceeding 300 lines** — proactive split before hitting the 500-line hard limit
- **Files with mixed responsibilities** — a module containing both data models and business logic
- **Before adding new features** — if adding a feature would push a file past 300 lines, split first, then add
- **During review-driven refactoring** — when adversarial review identifies a file as "doing too much"

**Do not use for:**
- Test files (exempt from line limits)
- Configuration files
- Generated code (auto-generated files should not be manually split)

## Related Decisions

- [[2026-02-17-singleton-consolidation-mandatory-during-file-splits]] — the key invariant this checklist enforces
- [[2026-02-23-enforce-no-orphan-modules-policy]] — file splits create orphan risk if not wired into the module tree
- [[2026-02-24-anti-pattern-disconnected-modules-without-consumers]] — what happens when a file split is done without this checklist
- [[2026-02-09-session-46-git-unification-complete]] — the git unification session that resolved 30+ file conflicts, a scenario where this checklist's caller-tracking prevents breaking changes

## Related Patterns

- [[private-to-public-rename-drift]] — renames during file splits are a common missed-caller scenario
- [[service-class-singleton-pattern]] — singleton management is the critical step in any file split
- [[async-singleton-lock-isolation]] — async singletons need additional care during splits (lock placement)
