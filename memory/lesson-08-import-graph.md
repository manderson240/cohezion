---
title: Import Graph Analysis: Map Dependencies Before Refactoring
date: 2026-02-23
severity: HIGH
category: coding
cost_of_forgetting: "Cascade import failures across 50+ files from a single module rename/move"
tags: [imports, dependencies, refactoring, graph-analysis]
status: validated
aspect: knower
neural:
  activation: 0.72
  stage: growing
  synapse_in: 6
  synapse_out: 5
---

# Lesson: Import Graph Analysis: Map Dependencies Before Refactoring

## Context

During the Cohezion GraphRAG implementation in February 2026, a module restructuring was attempted to improve code organization. The module `src.embeddings` was split into `src.embeddings.ollama` and `src.embeddings.batch`. The split was clean and tests for the embedding modules passed. However, 15+ other modules throughout the codebase imported from `src.embeddings` and broke simultaneously. The cascade of import failures took over an hour to fix because consumers were spread across multiple directories.

## Problem

Python import graphs are deeper and wider than developers typically realize:

1. **Transitive dependents**: A single module can have 50+ transitive dependents (modules that import modules that import it). Changing the module breaks them all.
2. **Circular imports**: Refactoring can introduce circular imports that are invisible until runtime. Python only detects circular imports when the import chain is executed.
3. **Missing `__init__` exports**: When splitting a module into a package, the original import paths break unless `__init__.py` re-exports the public interface.
4. **Dynamic imports**: `importlib.import_module()` and string-based imports are invisible to static analysis tools and IDE refactoring.

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

## Solution

The refactoring workflow now requires a mandatory import graph analysis step:

1. **Map all importers**: Use `grep` or `rg` to find every file that imports the target module
2. **Include transitive dependents**: Check if any of the importers are themselves imported by other modules
3. **Plan atomic update**: The module change and all consumer updates must be committed together
4. **Test the full graph**: Run tests for the changed module AND all its consumers, not just the module itself

This was also codified in the CI scope discipline (see [[lesson-20-ci-scope-discipline]]) to ensure CI runs tests for changed modules and their dependents.

## Prevention

- **Run import analysis before any rename/move/split**: This takes 30 seconds and prevents hours of cascade failures
- **Atomic consumer updates**: Never commit a module change without simultaneously updating all consumers
- **Maintain re-export `__init__.py`**: When splitting a module into a package, keep backward-compatible imports in `__init__.py`
- **Search for dynamic imports**: Check for `importlib.import_module()` patterns that static analysis misses

## Cost of Forgetting

- **Cascade import failures**: 15+ files break simultaneously from a single module change
- **1+ hour recovery time**: Finding and fixing all consumers across the codebase
- **CI failure cascade**: Every broken import is a test failure, blocking the pipeline
- **Circular import surprises**: Only discovered at runtime, potentially in production

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
- [[concept-modularity]] - import graph analysis is mandatory before any module restructuring
- [[knowledge-graph-semantic-relationships]] - import dependency graphs are a form of semantic relationship graph
- [[lesson-20-ci-scope-discipline]] - CI must run tests for changed modules and their dependents
- [[lesson-04-surgery-lesson]] - surgical changes minimize the blast radius that import graph analysis reveals

## Validation

**Discovered**: Feb 2026 during GraphRAG implementation -- 15+ files broken by module split
**Impact**: Refactoring workflow now includes mandatory import graph analysis
**Status**: Validated in production refactors
