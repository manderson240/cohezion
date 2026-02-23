---
title: YAML Folded Scalar Trap: Folded Blocks Collapse Newlines Into Spaces
date: 2026-02-23
severity: MEDIUM
category: tooling
tags: [yaml, configuration, parsing, data-format]
status: validated
---

# Lesson: YAML Folded Scalar Trap: Folded Blocks Collapse Newlines Into Spaces

## Context

YAML folded scalars (>) collapse newlines into spaces, while literal scalars (|) preserve newlines. Confusing the two causes configuration parsing errors or silently malformed multi-line strings.

## Core Learning

**Use | (literal) for multi-line strings that must preserve newlines. Use > (folded) only when whitespace collapsing is intentional.**

### Pattern
```yaml
# WRONG: folded collapses newlines
description: >
  Line 1
  Line 2
# Result: "Line 1 Line 2\n"

# RIGHT: literal preserves newlines
description: |
  Line 1
  Line 2
# Result: "Line 1\nLine 2\n"
```

## Recommendations

### Do
- Use | for multi-line strings where newlines matter
- Test YAML parsing: python3 -c "import yaml; print(yaml.safe_load(open('f.yaml').read()))"

### Don't
- Use > for code snippets in YAML

## Validation

**Discovered**: Feb 2026 in Cohezion configuration files
**Status**: Validated
