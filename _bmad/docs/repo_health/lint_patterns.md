# Lint Patterns Database

**Purpose:** Document common lint errors, their root causes, and how to fix them.
This is a learning resource for the team.

**Generated:** 2026-03-25
**Total Errors:** 9,245

---

## Critical Errors (Fix First)

### E722 - Bare Except Clause

**What it is:**
```python
# BAD - catches everything including KeyboardInterrupt
try:
    do_something()
except:  # ← Bare except!
    pass
```

**Why it's dangerous:**
- Catches `KeyboardInterrupt` (Ctrl+C) - user can't stop the program
- Catches `SystemExit` - breaks `sys.exit()` calls
- Hides bugs by silently swallowing unexpected exceptions
- Makes debugging nearly impossible

**How to fix:**
```python
# GOOD - catch specific exceptions
try:
    do_something()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
except FileNotFoundError:
    logger.warning("Config file not found, using defaults")
except Exception as e:  # Only if you really need catch-all
    logger.exception("Unexpected error")
    raise  # Re-raise so caller knows something failed
```

**Current Count:** 90 occurrences

**Pattern:** Usually found in:
- Quick-and-dirty scripts
- Error handlers that "should never fail"
- Legacy code from early development

---

### F821 - Undefined Name

**What it is:**
```python
# BAD - 'undefined_var' doesn't exist
result = undefined_var + 5
```

**Why it's critical:**
- Will cause `NameError` at runtime
- Usually means missing import or typo
- Can hide in conditionally executed code

**How to fix:**
1. Check if variable name is misspelled
2. Add missing import: `from module import undefined_var`
3. Define the variable before use
4. If it's optional, use: `undefined_var = None` at module level

**Current Count:** Present in error analysis

**Pattern:** Often occurs when:
- Refactoring without updating all references
- Copy-pasting code from different contexts
- Missing imports in conditional branches

---

### F405 - Import Star Undefined

**What it is:**
```python
# BAD - using undefined name from import *
from module import *

result = some_function()  # Where did this come from?
```

**Why it's problematic:**
- Makes code hard to understand
- No IDE autocomplete support
- Can accidentally import conflicting names
- Static analysis can't verify correctness

**How to fix:**
```python
# GOOD - explicit imports
from module import some_function, another_function

result = some_function()  # Clear where this comes from
```

**Current Count:** Present in error analysis

---

## High Priority Errors

### E501 - Line Too Long

**What it is:** Line exceeds 100 characters

**Why it matters:**
- Hard to read on smaller screens
- Breaks side-by-side diffs in PR reviews
- Triggers horizontal scrolling in editors

**How to fix:**
```python
# BAD
result = some_function(with_many_arguments, that_make_the_line, way_too_long_and_hard, to_read_on_small_screens)

# GOOD - multiple lines
result = some_function(
    with_many_arguments,
    that_make_the_line,
    way_too_long_and_hard,
    to_read_on_small_screens,
)

# GOOD - implicit continuation
result = (
    first_part + second_part + third_part
    + fourth_part + fifth_part
)

# GOOD - f-string breaking
message = (
    f"User {user_id} attempted {action} on {resource} "
    f"at {timestamp} with result {result}"
)
```

**Current Count:** 1,383 occurrences

**Pattern:** Very common, easy to auto-fix with `ruff check --fix`

---

### RUF013 - Implicit Optional

**What it is:**
```python
# BAD - implicit Optional
def process(value: str = None) -> str:  # Should be Optional[str]
    ...
```

**Why it matters:**
- PEP 484 requires explicit Optional
- Type checkers can't verify correctness
- Can lead to None-related bugs

**How to fix:**
```python
from typing import Optional

# GOOD - explicit Optional
def process(value: Optional[str] = None) -> str:
    if value is None:
        value = "default"
    return value

# Or Python 3.10+ syntax:
def process(value: str | None = None) -> str:
    ...
```

**Current Count:** Part of 1,445 high priority errors

---

## Medium Priority Errors

### I001 - Import Sorting

**What it is:** Imports not sorted according to PEP 8

**Order should be:**
1. Standard library (builtins)
2. Third-party packages
3. Local/application imports

**How to fix:**
```python
# BAD
import cohezion
import os
from flask import Flask
import sys

# GOOD
import os
import sys
from pathlib import Path

from flask import Flask

import cohezion
from cohezion.compound.executor import CompoundExecutor
```

**Auto-fix:** `ruff check --fix` handles this automatically

---

### E402 - Module Level Import Not at Top

**What it is:**
```python
# BAD
print("Starting...")
import os  # Import after code!
```

**Why it matters:**
- Imports should be at top for clarity
- Side effects from import happen unpredictably

**How to fix:** Move all imports to top of file

**Exception:** Conditional imports for optional dependencies are OK:
```python
# Acceptable
if TYPE_CHECKING:
    from typing import TypedDict  # Only imported during type checking
```

---

## Low Priority / Style Errors

### N806 - Variable Naming

**What it is:** Variable in function should be lowercase (snake_case)

**Examples:**
```python
# BAD
MyVariable = 5
UserName = "Alice"

# GOOD
my_variable = 5
user_name = "Alice"
```

---

### S101 - Assert Statements

**What it is:** Use of `assert` in production code

**Why it's flagged:**
- `assert` is removed when Python runs with `-O` (optimize) flag
- Shouldn't be used for validation that must always run

**When to use:**
- Internal consistency checks (invariants)
- Debugging aids
- Test code (pytest uses assert)

**When NOT to use:**
- Input validation
- Security checks
- Business logic validation

---

## Security Errors (S Series)

### S607 - Starting Process with Partial Path

**What it is:**
```python
# BAD - relies on PATH
subprocess.run(["python", "script.py"])

# GOOD - explicit path
subprocess.run([sys.executable, "script.py"])
subprocess.run(["/usr/bin/python3", "script.py"])
```

---

## Auto-Fix Strategy

**Can Auto-Fix (Safe):**
- E501 (line too long) - mostly
- I001 (import sorting)
- W293 (whitespace)
- UP006 (Python upgrade checks)

**Manual Review Required:**
- E722 (bare except) - needs proper exception selection
- F821 (undefined name) - needs analysis of intent
- RUF013 (implicit Optional) - needs type annotation decision

**Command to auto-fix:**
```bash
ruff check . --fix
```

---

## Prevention Strategies

1. **Pre-commit hooks** - Catch before commit
2. **IDE integration** - Real-time feedback
3. **CI enforcement** - Block merges with critical errors
4. **Code review checklist** - Manual verification
5. **Team training** - This document!

---

## Error Distribution by Directory

Based on current analysis:

- **cloud-vault-mcp/**: MCP server components (various errors)
- **src/cohezion/**: Core modules (import/style issues)
- **tests/**: Test files (assert statements expected)
- **scripts/**: Driver scripts (various issues)

---

## References

- [Ruff Rules Documentation](https://docs.astral.sh/ruff/rules/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [PEP 484 Type Hints](https://peps.python.org/pep-0484/)
