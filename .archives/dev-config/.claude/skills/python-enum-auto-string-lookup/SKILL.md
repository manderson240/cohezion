---
name: python-enum-auto-string-lookup
description: |
  Fix for ValueError or silent wrong-value lookups when calling EnumClass(string)
  on an enum that uses auto(). Use when: (1) ValueError: 'foo' is not a valid
  MyEnum, (2) enum uses auto() and you have a string key from a dict/config/user
  input, (3) code does MyEnum(some_string) and gets UNKNOWN/wrong member silently.
  Root cause: auto() assigns integer values (1,2,3...); EnumClass(value) is
  value-based lookup, not name-based. Fix: use EnumClass["NAME"] or a case-
  insensitive mapping dict.
author: Claude Code
version: 1.0.0
---

# Python Enum auto() String Lookup

## Problem

`auto()` enum members look like they should be addressable by name string, but
`EnumClass("name")` does *value* lookup (integers for `auto()`), not name lookup.
This causes either `ValueError` or silent fallback to a wrong/default member.

```python
from enum import Enum, auto

class IntentType(Enum):
    GENERATE = auto()   # value = 1
    ANALYZE  = auto()   # value = 2
    UNKNOWN  = auto()   # value = 7

# BROKEN: value-based lookup, "generate" != 1
IntentType("generate")   # → ValueError OR silently returns wrong member
IntentType("GENERATE")   # → ValueError (same reason)

# CORRECT: name-based lookup
IntentType["GENERATE"]   # → IntentType.GENERATE ✓
```

## Context / Trigger Conditions

- Enum uses `auto()` (not string values like `class MyEnum(str, Enum)`)
- Caller has a string key from a dict key, config file, user input, or API response
- Error: `ValueError: 'foo' is not a valid MyEnum`
- Symptom: always returns a default/UNKNOWN member when a string is passed

**Where this bit us in Cohezion:**
`request_alignment_analyzer.py` — `_classify_intent()` builds scores using
`_INTENT_KEYWORDS` dict (lowercase keys: `"generate"`, `"analyze"`, ...) then
called `IntentType(best_intent)`. Since `auto()` values are integers, the string
lookup always failed and fell through to `IntentType.UNKNOWN`.

## Solution

### Option A — `.upper()` name lookup (minimal fix, best when dict keys match enum names)

```python
# Before (broken):
return IntentType(best_intent), confidence

# After (fixed):
return IntentType[best_intent.upper()], confidence
```

Works when dict keys are lowercase versions of enum member names (e.g., `"generate"` → `GENERATE`).

### Option B — Case-insensitive mapping dict (robust, handles arbitrary casing)

```python
_INTENT_MAP = {name.lower(): member for name, member in IntentType.__members__.items()}

intent = _INTENT_MAP.get(best_intent.lower(), IntentType.UNKNOWN)
```

Handles any casing of the input string. Preferred when dict keys may not exactly
match enum names.

### Option C — Switch to str-valued enum (changes the definition)

```python
class IntentType(str, Enum):
    GENERATE = "generate"
    ANALYZE  = "analyze"
    UNKNOWN  = "unknown"

# Now value-based lookup works with strings:
IntentType("generate")  # → IntentType.GENERATE ✓
```

Trade-off: requires changing the enum definition and any code that compares `.value`.

## Verification

```bash
python -c "
from enum import Enum, auto
class IntentType(Enum):
    GENERATE = auto()
    UNKNOWN = auto()

# Option A
print(IntentType['GENERATE'])      # IntentType.GENERATE
print(IntentType['generate'.upper()])  # IntentType.GENERATE

# Option B
_map = {n.lower(): m for n, m in IntentType.__members__.items()}
print(_map.get('generate', IntentType.UNKNOWN))  # IntentType.GENERATE
"
```

## Quick Reference

| Syntax | Lookup type | Works with auto()? |
|--------|------------|-------------------|
| `MyEnum(value)` | Value-based | ❌ (auto values are ints) |
| `MyEnum["NAME"]` | Name-based | ✓ (case-sensitive) |
| `MyEnum.__members__["NAME"]` | Name-based | ✓ (same as above) |
| `MyEnum[key.upper()]` | Name-based | ✓ if key matches name |
