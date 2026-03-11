---
name: ruff-release-readiness-sweep
description: |
  Systematic lint triage workflow to prepare a Python codebase for release.
  Use when: (1) user asks to "clean up codebase for release", (2) pre-release
  quality sweep needed, (3) reducing lint errors from hundreds to style-only.
  Prioritizes real bugs (F821, syntax) over style issues (E501, N806) and uses
  ruff auto-fix to eliminate safe violations without manual edits.
author: Claude Code
version: 1.0.0
---

# Ruff Release Readiness Sweep

## Problem

A codebase has accumulated hundreds of lint violations. Not all are equal —
some are real runtime bugs (undefined names, syntax errors), others are style
preferences (line length, naming). Fixing them in the wrong order wastes time.

## Priority Order (Fix in This Sequence)

| Priority | Rule(s) | Why | Action |
|----------|---------|-----|--------|
| 1 | Syntax errors (E9xx) | File can't even be parsed | Fix manually |
| 2 | F821 (undefined-name) | Real runtime `NameError` bugs | Fix manually |
| 3 | F811 (redefined-while-unused) | Duplicate definitions / dead code | Fix manually |
| 4 | E741 (ambiguous-variable-name) | `l` vs `1` confusion | Rename manually |
| 5 | F401 (unused-import) | Dead imports | `ruff check --fix` |
| 6 | W29x (whitespace) | Trailing/mixed whitespace | `ruff check --fix` |
| 7 | F841 (unused-variable) | Minor: assigned but never read | Optional |
| 8 | E501 (line-too-long) | Style only | Optional / skip |
| 9 | N806/N812/N814 (naming) | Often intentional (math vars) | Optional / skip |

## Workflow

```bash
# Step 1: Get full picture (save output for tracking)
ruff check src/ 2>&1 | tee /tmp/lint_before.txt
grep -c "error" /tmp/lint_before.txt  # total count

# Step 2: Identify critical violations
ruff check src/ | grep -E "^.*\s(E9|F821|F811|E741)" | head -50

# Step 3: Fix critical violations manually (see patterns below)

# Step 4: Apply safe auto-fixes
ruff check src/ --fix --select F401,W291,W293,W292,F541,E711,E712

# Step 5: Verify improvement
ruff check src/ 2>&1 | tee /tmp/lint_after.txt
grep -c "error" /tmp/lint_after.txt

# Step 6: Confirm tests still pass
uv run pytest tests/ -q
```

## Common F821 Patterns (Undefined Name)

### Comprehension variable typo
```python
# WRONG: unpacks as (_, _, ts) but uses t
recent = [t for _, _, ts in self.history if time.time() - ts < 3600]

# CORRECT: use the actual unpacking variable
recent = [ts for _, _, ts in self.history if time.time() - ts < 3600]
```

### Missing import for used name
```python
# WRONG: asyncio used but not imported
async def restart():
    await asyncio.sleep(1)  # NameError at runtime

# CORRECT: add the import
import asyncio
```

### TYPE_CHECKING guard for forward references
```python
# WRONG: circular import
from cohezion.compound.thermodynamic_metrics import ThermodynamicState

# CORRECT: type-only import (no runtime cost)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cohezion.compound.thermodynamic_metrics import ThermodynamicState
```

### Dead code after unconditional raise (F821 false positive)
Code after `raise SomeException(...)` can never execute, but ruff still
validates it. Options: delete the dead code, or restructure to avoid.

## Common F811 Patterns (Redefined While Unused)

### Duplicate class methods (second definition wins, first is dead)
```python
class MyClass:
    def get_truth_anchors(self): ...  # DEAD — defined again below
    def remember_fact(self): ...      # DEAD
    # ... 300 lines of other methods ...
    def get_truth_anchors(self): ...  # LIVE — this is the one that runs
    def remember_fact(self): ...      # LIVE
```
Fix: delete the earlier (dead) definitions.

### Import shadowed by local class definition
```python
from module import CompoundCycleResult, CompoundCycleReport  # imported
# ... later in same file ...
class CompoundCycleResult: ...   # shadows the import — F811
class CompoundCycleReport: ...   # shadows the import — F811
```
Fix: remove the shadowed imports from the `from ... import` statement.

## Common E741 Patterns (Ambiguous Variable Name)

```python
# WRONG: l looks like 1
lines = [l for l in content.splitlines()]
lv = tuple(int(x) for x in latest.split("."))

# CORRECT: rename to descriptive alternatives
lines = [ln for ln in content.splitlines()]   # ln for "line"
lv = tuple(int(x) for x in latest.split(".")) # lv for "latest version"
```

## Gamma Release Decision Criteria

After sweep, categorize remaining violations:
- **Block release**: Any F821, syntax errors, F811 with active duplicates
- **Acceptable for gamma**: F841 (unused vars), E501 (line length), N806 (naming)
- **Post-gamma cleanup**: Files over 500-line limit, large-scale refactors

A codebase is gamma-ready when ALL critical violations are zero,
even if style violations remain.

## Verification

```bash
# Confirm zero critical violations
ruff check src/ | grep -cE "F821|F811|E741|E9[0-9]{2}" || echo "0 critical"

# Confirm test suite intact
uv run pytest tests/ -q --tb=no | tail -3
```
