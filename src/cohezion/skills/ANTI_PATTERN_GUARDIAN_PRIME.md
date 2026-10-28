---
name: anti-pattern-guardian
description: Automated detection and remediation of codebase anti-patterns. 
  Scans for AGENTS.md documented issues including mock isolation, async blocking,
  singleton pollution, and bare exception handlers. Use when reviewing code or
  setting up CI quality gates.
metadata:
  version: "0.1"
  generated_from: "AGENTS.md mining"
---

# SKILL: ANTI_PATTERN_GUARDIAN_PRIME

## DOMAIN EXPERTISE

You are the **Anti-Pattern Guardian** - detecting code constructs that violate
Cohezion engineering standards before they cause issues.

## ANTI-PATTERNS DATABASE

### Blocking I/O in Async Function (10 instances)
- **Severity:** critical
- **Category:** async-pattern
- **Detection:** `requests.get(url).json()...`
- **Remediation:** Use httpx.AsyncClient or asyncio.to_thread for blocking calls
- **Files Affected:** 8

### Bare pip Install (7 instances)
- **Severity:** medium
- **Category:** dependency-management
- **Detection:** `pip install...`
- **Remediation:** Use uv for all Python package operations
- **Files Affected:** 6

### Bare Exception Handler (181 instances)
- **Severity:** high
- **Category:** error-handling
- **Detection:** `except:...`
- **Remediation:** Use specific exception types with circuit breakers
- **Files Affected:** 104

### Insecure Dynamic Fallbacks (Phantom Eval)
- **Severity:** critical
- **Category:** security-and-invariance
- **Detection:** `eval(compile(...))` or `eval()` left behind a safe parser
- **Remediation:** Explicit failure > implicit approximation. Fail loudly with `UnsupportedNodeError`; never leave insecure dynamic fallbacks behind safe AST parsers.

### Compatibility Passthrough Shims
- **Severity:** medium
- **Category:** code-bloat
- **Detection:** Function body only forwards arguments (`def foo(*a, **k): return _foo(*a, **k)`)
- **Remediation:** Shims are debt, not courtesy. Use direct `__all__` re-exports or clean automated codemods.

### CPython Empty-Namespace Exec Builtins Trap
- **Severity:** critical
- **Category:** sandbox-escape
- **Detection:** `namespace = {}; exec(code, namespace)`
- **Remediation:** Default-deny execution. CPython auto-injects builtins (`open`, `os`, `sys`) into empty dicts. Strictly pass `safe_exec_globals()` or compile to deterministic AST bytecode. Enforced by `scripts/ci/autoharness_gate.py`.

### Agent Inheritance Hierarchy Bloat
- **Severity:** high
- **Category:** architectural-complexity
- **Detection:** Class hierarchies with >10 `__init__` parameters implementing duplicate `execute_task` loops
- **Remediation:** Agents are flows, not objects. Compose pure functional pipelines using Python 3.13 Protocols and frozen `@dataclass(slots=True)`.


## INSTRUCTION

### 1. Scan Codebase
```bash
python3 .pi/integrations/anti_pattern_scanner.py
```

### 2. Review Findings
Check `.pi/integrations/anti_pattern_inventory.json` for:
- Critical severity (fix immediately)
- High severity (fix before commit)
- Medium severity (address in backlog)

### 3. Auto-Remediate
For detected instances, suggest:
- Mock isolation: Use @patch at source
- Async blocking: Replace requests with httpx
- Singleton reset: Add conftest.py fixture
- Exceptions: Use specific error types

### 4. CI Integration
Add to pre-commit hooks:
```yaml
- repo: local
  hooks:
  - id: anti-pattern-guardian
    entry: python3 .pi/integrations/anti_pattern_scanner.py
    language: python
```

## PATTERNS

### Critical Pattern
- Always scan before major refactoring
- Fix critical anti-patterns first
- Document exceptions in code comments  

## CITATIONS
- AGENTS.md (source of truth for anti-patterns)
- PatternRepository (Cohezion persistence layer)

## VERSION
v0.1 - Initial scan results from AGENTS.md mining

## SEE ALSO
- PI_INTEGRATION_PRIME.md
- TESTING_PRIME.md
- RELIABILITY_PRIME.md


## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for ANTI PATTERN GUARDIAN PRIME.
- **AutoHarness Invariants**: 0ms AST bytecode policy assertions (arXiv:2603.03329v1).
- **Deterministic Execution**: Zero-latency verification and sovereign local execution.
