---
title: Import Graph Analysis: Map Dependencies Before Refactoring
date: 2026-02-23
severity: HIGH
category: coding
tags: [imports, dependencies, refactoring, graph-analysis]
status: validated
---

# Lesson: Import Graph Analysis: Map Dependencies Before Refactoring

## Context

Refactoring a module without understanding its import graph leads to cascade failures across unrelated files. When a module is renamed or restructured, all importers break simultaneously.

## Core Learning

**Before any refactoring, build the import graph. Know every consumer before touching the module.**

### Why This Matters
- Python import graphs can have 50+ transitive dependents on a single module
- Circular imports become visible only after refactoring
- Missing __init__ exports are invisible until runtime

### Pattern
```bash
# Find all files that import target module
grep -r "from src.module import" . --include="*.py"
grep -r "import src.module" . --include="*.py"

# Or use vexor for semantic search
vexor search "imports from module_name" --mode code --ext .py
```

## Recommendations

### Do
- Run import graph analysis before any module move/rename/split
- Update ALL consumers atomically with the module change
- Use the Grep tool to find all importers

### Don't
- Refactor a module and assume tests will catch all consumer breakage
- Trust IDE refactor tools to find all dynamic imports

## Related Concepts

- [[compound-engineering]] - Graph-aware refactoring is prerequisite for safe compound changes

## Validation

**Discovered**: Feb 2026 during GraphRAG implementation
**Status**: Validated in production refactors
