---
title: Operation-Specific Modulation: Apply Validation Intensity by Operation Risk
date: 2026-02-23
severity: HIGH
category: architecture
cost_of_forgetting: "Low-risk ops slow down unnecessarily; high-risk ops under-validated leading to data loss or corruption"
tags: [validation, risk-management, operational, modulation]
status: validated
aspect: knower
neural:
  activation: 0.75
  stage: growing
  synapse_in: 9
  synapse_out: 7
---

# Lesson: Operation-Specific Modulation: Apply Validation Intensity by Operation Risk

## Context

During Cohezion compound engineering design in February 2026, the validation framework was applying identical validation intensity to every operation. A simple read query went through the same multi-step pre-condition check as a destructive delete. This created two simultaneous problems: read-heavy workflows were unnecessarily slow, and the uniform validation gave a false sense of security for high-risk operations that needed deeper checks.

## Problem

Uniform validation creates perverse incentives:

1. **Over-validation of reads**: Simple query and list operations passed through schema validation, pre-condition checks, and logging -- adding 50-100ms of overhead per call for zero safety benefit. In batch read scenarios, this overhead accumulated to seconds.
2. **Under-validation of writes**: Destructive operations (delete, overwrite, git force-push) received the same single-pass validation as reads. Because validation was "checked" at the same level, developers assumed destructive operations were safe. They were not -- they needed dry-run, confirmation, and full pre-condition verification.
3. **Validation fatigue**: When every operation triggers the same validation noise, developers stop paying attention to validation results. The signal drowns in noise.

## Core Learning

**Modulate validation intensity by operation risk. Match rigor to consequence, not to uniformity.**

### Risk Levels and Validation
```
LOW RISK (read, query, list):
  - Single validation check
  - Failure logged as warning

MEDIUM RISK (write, create, modify):
  - Schema validation required
  - Pre-condition check
  - Failure logged as error with rollback

HIGH RISK (delete, overwrite, push, history-rewrite):
  - Full pre-condition verification
  - Explicit user confirmation required
  - Dry-run first if possible
```

## Solution

Operations are now classified by risk level at design time, and each level has a corresponding validation template:

- **Low risk**: Lightweight validation (type checks only). Fast path for read-heavy workloads.
- **Medium risk**: Schema validation with pre-condition checks. Failures trigger error logging and automatic rollback where possible.
- **High risk**: Full pre-condition verification, explicit user confirmation via `AskUserQuestion`, and dry-run before execution. This is the pattern used for git force operations, database deletes, and history rewrites.

The risk classification is part of the operation interface definition, not an afterthought.

## Prevention

- **Classify at design time**: Every new operation gets a risk classification in its interface definition
- **Build validation into the operation**: Don't rely on callers to add appropriate validation; the operation itself enforces its risk-appropriate checks
- **Audit risk classifications periodically**: As operations evolve, their risk levels may change (e.g., a read that now has side effects)
- **Never let urgency override risk classification**: The cost of a failed high-risk operation always exceeds the time saved by skipping validation

## Cost of Forgetting

- **Slow read paths**: Over-validated reads add latency to the most common operations
- **Under-protected destructive operations**: Data loss or corruption from insufficiently validated deletes/overwrites
- **Validation fatigue**: Developers stop reading validation output when every operation triggers the same checks
- **False security**: Uniform validation gives the illusion that all operations are equally safe

## Recommendations

### Do
- Classify each operation by risk level at design time
- Build risk-appropriate validation into operation implementations

### Don't
- Apply the same validation to reads and writes
- Let urgency override risk-appropriate validation

## Related Concepts

- [[compound-engineering]] - Risk-modulated validation enables safe compound operations
- [[service-layer-architecture]] - service layers implement risk-modulated validation naturally: read endpoints have different validation intensity than write/delete endpoints
- [[lesson-12-layered-validation]] - complementary lesson: validate at every boundary, but modulate intensity by risk at each boundary
- [[lesson-03-critical]] - critical operations require the HIGH RISK validation pattern with explicit verification
- [[ai-safety]] - operation risk classification is a safety pattern: high-risk operations must have safety gates
- [[concept-validation]] - operation-specific validation intensity is a refinement of the general validation principle
- [[api-design]] - API operation classification (GET vs DELETE) maps directly to risk-level validation

## Validation

**Discovered**: Feb 2026 in Cohezion compound engineering design
**Status**: Validated -- referenced 14+ times across project (high-impact lesson)
