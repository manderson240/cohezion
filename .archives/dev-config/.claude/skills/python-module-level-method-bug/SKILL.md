---
name: python-module-level-method-bug
description: |
  Fix for class methods accidentally defined at module level due to wrong indentation.
  Use when: (1) AttributeError: 'ClassName' object has no attribute 'method_name'
  but the method clearly appears in the file, (2) method was recently added or
  refactored and only fails at runtime call sites, (3) the method exists in the
  file but is not inside the class body (indentation off by one level).
  Key insight: Python treats the function as module-level — no syntax error, no
  import error, just a missing instance method.
author: Claude Code
version: 1.0.0
---

# Python Class Method Accidentally at Module Level

## Problem

A method that appears to belong to a class is actually defined at module scope
because its indentation is wrong. Python silently accepts this — the function
becomes a module-level callable, not a class method. Instances won't have it.

This commonly happens after:
- Merge conflicts that shift indentation
- Copy-pasting a method below the class
- Editor auto-indent failures on large classes

## Context / Trigger Conditions

- `AttributeError: 'ClassName' object has no attribute 'method_name'` at runtime
- The method IS in the file (grep confirms it exists)
- The class definition and method definition are in the same file
- Bug was introduced during a refactoring or merge
- Ruff may not flag this (both are syntactically valid Python)

## Solution

1. Check the method's indentation visually or with a linter:

```bash
# Find the method and check surrounding indentation
grep -n "def to_dict\|class MyClass" src/path/to/file.py
```

2. Verify the class body ends AFTER the method:

```python
# WRONG — method at module level (0 indentation for def):
class MCPServerConfig:
    name: str
    port: int

def to_dict(self) -> dict:   # <-- module level! instances have no .to_dict()
    return {"name": self.name}

# CORRECT — method inside class (4-space indentation for def):
class MCPServerConfig:
    name: str
    port: int

    def to_dict(self) -> dict:   # <-- class method
        return {"name": self.name}
```

3. Fix by indenting the method body 4 spaces (or one level) into the class.

4. Also look for orphaned code fragments directly below the misplaced method:
   in `server_manager.py`, orphaned dict-literal fragments (lines 79-82) caused
   10 syntax errors in ruff because they were outside any function context.

## Verification

```bash
# Confirm method is now accessible on instances
python -c "from mymodule import MyClass; obj = MyClass(); obj.to_dict()"

# Run ruff to catch any remaining syntax issues
ruff check src/path/to/file.py
```

## Example

Real case from `src/cohezion/mcp/manager/server_manager.py`:

```python
# Before (broken): to_dict() at module level
@dataclass
class MCPServerConfig:
    name: str
    port: int
    # ...

def to_dict(self) -> dict[str, Any]:   # wrong indentation
    safe_env = {}
    # ...

{"name": self.name, "port": self.port}  # orphaned fragment → 10 syntax errors

# After (fixed): to_dict() inside the class
@dataclass
class MCPServerConfig:
    name: str
    port: int

    def to_dict(self) -> dict[str, Any]:   # 4-space indent = class method
        safe_env = {}
        # ...
        return {"name": self.name, "port": self.port, ...}
```
