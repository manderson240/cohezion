---
title: Critical Operations Require Explicit Verification Before Proceeding
date: 2026-02-23
severity: CRITICAL
category: operational
cost_of_forgetting: "Data loss, system corruption, or irreversible damage from unverified destructive operations"
tags: [verification, safety, critical-operations]
status: validated
aspect: knower
neural:
  activation: 0.74
  stage: growing
  synapse_in: 10
  synapse_out: 6
---

# Lesson: Critical Operations Require Explicit Verification Before Proceeding

## Context

Across multiple Cohezion sessions, incidents occurred where agentic workflows executed destructive operations based on stale or assumed state. The most significant involved a `git reset --hard` that discarded uncommitted work because the agent assumed the working tree was clean (it had been clean 5 minutes earlier, but a concurrent process had written new files). Other incidents included database deletions where the target records had already been modified by another session.

## Problem

Agentic systems execute operations faster than humans can review them. This speed becomes dangerous when:

1. **State drift**: The system state at execution time differs from state at planning time. A file that existed when the plan was made may have been deleted. A branch that was clean may now have uncommitted changes.
2. **Chained destructive operations**: Agent loops can chain multiple destructive operations in sequence. A failure in early verification propagates through the chain.
3. **Confidence substituting for evidence**: The agent "knows" the state should be safe based on recent reads, but does not re-verify at execution time. Confidence is not proof.

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

## Solution

Critical operations now follow a mandatory verification protocol:

1. **Classification**: Operations are classified by risk level at design time (see [[lesson-31-operation-specific-modulation]])
2. **Precondition enumeration**: Before execution, the agent lists all preconditions explicitly in the session
3. **Live verification**: Each precondition is checked with a fresh read or query -- not from cached state
4. **Verification logging**: Results are logged so the verification can be audited
5. **Gated execution**: The operation proceeds only if ALL preconditions pass; any failure halts the operation

## Prevention

- **Classify operations by risk at design time**: Do not discover that an operation is destructive after running it
- **Re-read state immediately before execution**: Never rely on reads from earlier in the session
- **Treat plan approval as separate from precondition verification**: A plan says "what to do"; verification confirms "it is safe to do it now"
- **Never skip under pressure**: Context pressure, time pressure, and "just this once" are the conditions where verification matters most

## Cost of Forgetting

- **Data loss**: Destructive operations on wrong targets (wrong branch, wrong records, wrong files)
- **System corruption**: Partially completed destructive operations that leave inconsistent state
- **Irreversible damage**: Operations like history rewrite, force push, or database delete cannot be undone
- **Multi-session recovery cost**: See [[lesson-13-8-6m-file-incident]] for an example of recovery complexity

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
- [[operational-data-ai-agents]] - verifying actual system state before critical operations is agents using operational data as their senses
- [[lesson-31-operation-specific-modulation]] - risk classification determines which operations require full critical verification
- [[ai-safety]] - explicit verification before destructive operations is a core AI safety pattern
- [[adversarial-review]] - adversarial review before execution catches assumptions that verification alone may miss
- [[lesson-13-8-6m-file-incident]] - example of the recovery cost when critical verification is skipped

## Validation

**Discovered**: Feb 2026 across multiple incidents involving stale state assumptions
**Status**: Core operational principle across Cohezion sessions -- now encoded in verification rules
