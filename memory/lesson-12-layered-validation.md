---
title: Layered Validation: Validate at Each System Boundary, Not Just at Entry
date: 2026-02-23
severity: HIGH
category: architecture
cost_of_forgetting: "Corrupt data propagates silently through internal layers, causing cryptic failures far from the source"
tags: [validation, system-design, data-integrity, boundary-testing]
status: validated
aspect: knower
neural:
  activation: 0.524
  stage: growing
  cluster: lessons
---

# Lesson: Layered Validation: Validate at Each System Boundary, Not Just at Entry

## Context

During Cohezion phase 1 production validation, the agent pipeline consisted of multiple layers: an API ingestion layer, a service processing layer, a SurrealDB storage layer, and a consumer/reporting layer. Initially, validation was performed only at the API entry point. Data that passed the API schema check was trusted implicitly as it flowed through the rest of the stack.

## Problem

Entry-only validation created a class of failures where corrupt or malformed data slipped through the API check (or was introduced by intermediate processing steps) and propagated deep into the system:

1. **Cryptic database errors**: A service layer produced records with missing required fields. The database layer received them and threw errors that pointed to the storage code, not the actual source of the malformation.
2. **Silent data corruption**: A processing step produced valid-looking but semantically incorrect data (e.g., session IDs with wrong format). Downstream consumers processed it without error but produced wrong results.
3. **Debugging difficulty**: Each failure required tracing data flow across 3-4 layers to find where validation should have caught the problem. Average debugging time: 30-45 minutes per incident.

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

## Solution

Validation was added at every system boundary using typed schemas:

- **API boundary**: Pydantic models validate incoming requests (structure and types)
- **Service boundary**: Business rule validation (semantic correctness, preconditions)
- **Database boundary**: Schema assertions before writes (required fields, type constraints)
- **Consumer boundary**: Output validation before delivering results to users or downstream agents

Each layer can be tested independently. A failure at any boundary produces a clear error message pointing to the exact boundary where validation failed, reducing debugging time from 30-45 minutes to under 5 minutes.

## Prevention

- **Use Pydantic or dataclasses at every boundary**: Never pass raw dicts between system layers
- **Fail fast**: Raise errors at the first boundary that detects invalid data, rather than passing it along
- **Test each layer independently**: Unit tests should validate that each boundary rejects invalid input correctly
- **Monitor validation failures**: Log validation errors at each boundary to detect patterns of upstream data quality problems

## Cost of Forgetting

- **30-45 minutes per debugging incident** tracing data corruption through multiple layers
- **Silent data corruption** that produces incorrect downstream results without any error
- **Cascading failures** when corrupt data reaches a layer that cannot handle it
- **Lost trust in the data pipeline** -- once consumers see incorrect data, they lose confidence in all results

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
- [[circleci-ai-cicd-validation]] - CircleCI's Chunk autonomous agent applies layered validation (diff analysis, dependency graphs, historical behavior) at each CI boundary
- [[service-layer-architecture]] - Service layer design depends on boundary-by-boundary validation to keep each layer independently correct
- [[concept-validation]] - concept validation in the vault knowledge graph applies this same layered principle: validate at each boundary where knowledge enters the system
- [[api-design]] - validate at each API boundary; corrupt data propagates to cryptic failures otherwise
- [[lesson-31-operation-specific-modulation]] - validation intensity should be modulated by operation risk, but validation presence at every boundary is non-negotiable
- [[concept-isolation]] - each validation boundary creates an isolation point that prevents data corruption from crossing system layers

## Validation

**Discovered**: Feb 2026 in phase 1 production validation
**Impact**: Reduced debugging time from 30-45 minutes to under 5 minutes per incident
**Status**: Validated in production pipelines
