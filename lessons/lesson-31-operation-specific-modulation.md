---
title: Operation-Specific Modulation: Apply Validation Intensity by Operation Risk
date: 2026-02-23
severity: HIGH
category: architecture
tags: [validation, risk-management, operational, modulation]
status: validated
---

# Lesson: Operation-Specific Modulation: Apply Validation Intensity by Operation Risk

## Context

Applying uniform validation intensity across all operations wastes time on low-risk operations and under-validates high-risk ones.

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

## Recommendations

### Do
- Classify each operation by risk level at design time
- Build risk-appropriate validation into operation implementations

### Don't
- Apply the same validation to reads and writes
- Let urgency override risk-appropriate validation

## Related Concepts

- [[compound-engineering]] - Risk-modulated validation enables safe compound operations
- [[mcp-infrastructure-architecture]] - MCP tool operations need risk classification
- [[service-layer-architecture]] - service layers implement risk-modulated validation naturally: read endpoints have different validation intensity than write/delete endpoints, matching the risk levels described in this lesson

## Validation

**Discovered**: Feb 2026 in Cohezion compound engineering design
**Status**: Validated -- referenced 11 times across project (high-impact lesson)
