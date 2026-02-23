---
title: Critical Operations Require Explicit Verification Before Proceeding
date: 2026-02-23
severity: CRITICAL
category: operational
tags: [verification, safety, critical-operations]
status: validated
---

# Lesson: Critical Operations Require Explicit Verification Before Proceeding

## Context

In agentic workflows, certain operations are irreversible, have large blast radius, or depend on state that may have changed. Proceeding without explicit verification of preconditions leads to data loss or system corruption.

## Core Learning

**Any operation tagged CRITICAL must have preconditions verified explicitly before execution -- no implicit assumptions.**

### Why This Matters
- Agentic systems move fast and can chain destructive operations
- State changes between planning and execution invalidate assumptions
- Irreversible operations require proof, not confidence

### Pattern
```
1. Identify operation as CRITICAL
2. List all preconditions explicitly
3. Verify each precondition with a read/query (not assumption)
4. Log verification results before proceeding
5. Only execute if ALL preconditions verified
```

## Recommendations

### Do
- Enumerate preconditions before any critical operation
- Use actual system state (reads, queries) not mental model
- Log the verification results in the session

### Don't
- Proceed on "I think this is safe"
- Skip verification when under context or time pressure
- Treat plan approval as equivalent to precondition verification

## Related Concepts

- [[compound-engineering]] - Safety gates compound into reliable pipelines

## Validation

**Status**: Core operational principle across Cohezion sessions
