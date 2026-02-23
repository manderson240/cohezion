---
title: Layered Validation: Validate at Each System Boundary, Not Just at Entry
date: 2026-02-23
severity: HIGH
category: architecture
tags: [validation, system-design, data-integrity, boundary-testing]
status: validated
---

# Lesson: Layered Validation: Validate at Each System Boundary, Not Just at Entry

## Context

Systems that validate only at the entry point allow corrupt data to propagate through internal layers, where it causes cryptic failures far from the source.

## Core Learning

**Validate data at every system boundary: API to service, service to database, database to consumer. Each layer must be independently correct.**

### Pattern
```python
# Layer 1: API boundary
class AgentInput(BaseModel):
    session_id: str
    task: str

# Layer 2: Service boundary (business rules)
def validate_session(session_id: str) -> bool:
    return session_id.startswith("session-") and len(session_id) < 100

# Layer 3: Database boundary
def store_agent_output(data: dict):
    assert "session_id" in data and "result" in data
    db.create(data)
```

## Recommendations

### Do
- Add validation at each service-to-service call
- Use typed schemas (Pydantic, dataclasses) throughout the stack
- Fail fast at boundaries rather than propagating bad data

### Don't
- Assume data is clean inside the system boundary
- Use dict types without schemas for cross-service data

## Related Concepts

- [[compound-engineering]] - Layered validation is foundational to compound system reliability

## Validation

**Discovered**: Feb 2026 in phase 1 production validation
**Status**: Validated in production pipelines
