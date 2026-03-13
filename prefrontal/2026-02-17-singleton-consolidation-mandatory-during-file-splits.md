---
title: 'Singleton Consolidation Mandatory During File Splits'
date: '2026-02-17'
status: accepted
tags: [decision, singleton, refactoring, python, architecture]
aspect: thinker
neural:
  activation: 0.72
  stage: growing
  synapse_in: 4
  synapse_out: 6
---

# Singleton Consolidation Mandatory During File Splits

## Context

During a file split refactoring (breaking a large module into smaller focused modules), a singleton class was inadvertently duplicated: both the original file and the new split file contained a copy of the singleton. Because Python's singleton pattern uses a class-level `_instance` attribute, the two copies maintained independent `_instance` references — creating two distinct "singletons" in the same process.

The bug was invisible in most scenarios: individual tests passed because they only imported one module. But the full test suite (which imported both modules) experienced state inconsistency — changes made through one singleton were not visible through the other. Tests passed individually but flaked in the suite — the classic isolation failure signature.

Cost of this bug: 3 extra verification iterations (~50K tokens wasted) debugging test flakes before the root cause was identified.

## Decision

**Singleton consolidation is a mandatory step during any file split refactoring.** When splitting a file that contains a singleton:

1. **Identify all singletons** in the file being split (grep for `_instance`, `__new__`, `@classmethod` patterns)
2. **Choose a canonical home** — the singleton lives in exactly one module
3. **All other modules import from the canonical home** — never copy the class definition
4. **Update conftest.py** — singleton reset fixtures must reference the canonical import path
5. **Verify with `grep -rn "class ClassName" src/`** — exactly one definition must exist

## Consequences

**Positive:**
- Eliminates duplicate singleton state, which causes the most insidious test flakes
- Forces explicit decision about where each singleton lives during splits
- The grep verification step catches duplicates before they reach the test suite
- Prevents the ~50K token debugging cost observed in the incident

**Negative:**
- Adds a mandatory step to file split refactoring (overhead is minimal — 5 minutes)
- Requires developers to understand the singleton pattern and its failure modes
- May delay file splits if singleton consolidation reveals unexpected dependencies

## Alternatives Considered

**Allow duplicate singletons with shared state (module-level variable):** Use a module-level `_instance` variable that both copies reference. Rejected because this creates a hidden coupling between modules — the purpose of file splits is to reduce coupling, not introduce it through shared mutable state.

**Registry pattern instead of singleton:** Replace singletons with a service registry that manages instance lifecycle. Would solve the problem more generally but is over-engineering for the current codebase size. Deferred to post-alpha if the singleton count grows beyond 5.

**Linting rule to prevent duplicate class names:** Add a custom linting rule that flags duplicate class definitions across modules. Partially implemented — the manual grep step serves this purpose for now. A proper lint rule is a future improvement.

## Related

- [[safe-file-split-checklist]] — the checklist that enforces singleton consolidation during splits
- [[service-class-singleton-pattern]] — the correct singleton pattern that avoids duplicate instances
- [[async-singleton-lock-isolation]] — async-specific singleton isolation needed during file splits to prevent event loop binding issues
- [[2026-02-22-asyncio-lock-in-init-not-class-level]] — related class-level singleton lock issue discovered 5 days later; same root cause family
- [[private-to-public-rename-drift]] — renames during file splits are another common source of missed callers
- [[2026-02-23-enforce-no-orphan-modules-policy]] — orphan modules are a secondary risk of file splits without this checklist
