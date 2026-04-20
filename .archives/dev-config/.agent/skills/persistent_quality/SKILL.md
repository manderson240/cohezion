---
name: Persistent Quality
description: Maintain high-quality code output through pattern extraction, anti-pattern detection, and continuous improvement
triggers:
  - code review
  - quality check
  - pattern extraction
---

# Persistent Quality Skill

## Purpose
Ensure consistent quality in code generation by applying patterns extracted from the Cohezion codebase and avoiding known anti-patterns.

## When to Use
- Generating new code files
- Reviewing existing code
- Creating new skills or documentation
- Implementing complex features

## Instructions

### 1. Quality Checklist
Before completing any code generation task, verify:
- [ ] Type hints on all functions
- [ ] NumPy-style docstrings on public functions
- [ ] Error handling with circuit breaker pattern
- [ ] Tests written for new functionality
- [ ] No placeholder content

### 2. Pattern Application
Apply these verified patterns:
```python
# Circuit breaker for external calls
from cohezion.reliability import get_circuit
breaker = get_circuit("service_name", failure_threshold=5)

# Connection pooling
from cohezion.reliability.pool import get_pool
pool = get_pool("service", "http://localhost:8080", max_connections=20)

# Self-healing integration
from cohezion.healing import get_healing_system
system = get_healing_system()
```

### 3. Anti-Pattern Detection
Reject code containing:
- Hardcoded secrets or API keys
- Blocking I/O without timeout
- Magic numbers without constants
- Duplicate code blocks (extract to functions)
- Missing error handling

### 4. Self-Evaluation
Run SELF_EVALUATION_PRIME criteria:
- Coverage score ≥ 0.85
- Reference integrity check
- Semantic alignment validation

### 5. Documentation
Document significant decisions in:
- `src/cohezion/knowledge_graph/KEY_LEARNINGS.md`
- Skill files if new patterns emerge

## Resources
- [Skills Directory](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/)
- [KEY_LEARNINGS](file:///home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/KEY_LEARNINGS.md)
- [SELF_EVALUATION_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SELF_EVALUATION_PRIME.md)
