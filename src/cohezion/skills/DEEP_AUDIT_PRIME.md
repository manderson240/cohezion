# SKILL: DEEP_AUDIT_PRIME

## DOMAIN EXPERTISE
Deep static analysis of Python codebase for quality, complexity, and performance.

## CAPABILITIES
- **Complexity Analysis:** Cyclomatic complexity estimation
- **Blocking I/O Detection:** Finds synchronous calls in async functions
- **Architecture Scanning:** Import depth and coupling
- **Classification:** Categorizes modules as Good/Warning/Refactor

## USAGE
Run the auditor:
```bash
python src/cohezion/healing/deep_audit.py
```

## INTERPRETING RESULTS
- **Critical:** Blocking I/O or syntax errors (Fix immediately)
- **Refactor Candidate:** Complexity > 25 or LOC > 300 (Plan refactoring)
- **Warning:** Complexity > 15 (Monitor)

## SEE ALSO
- src/cohezion/healing/deep_audit.py
- src/cohezion/healing/utilization_audit.py
