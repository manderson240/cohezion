---
name: mutable-state-testing-trap
description: |
  Fix for false test equality when testing mutable objects that update in-place.
  Use when: (1) two sequential calls on same instance produce equal results unexpectedly,
  (2) testing graduated/scaled behavior where call N modifies the same state object as call N-1,
  (3) assertions like `state2.factor > state1.factor` always fail even though values differ.
  Root cause: both variables point to the same mutated object reference.
author: Claude Code
version: 1.0.0
---

# Mutable State Testing Trap

## Problem

When an object mutates `self.state` in-place and returns it, two sequential calls on the same instance return the SAME object reference. Comparing returned values always compares the final (last-written) state.

## Context / Trigger Conditions

```python
gov = SubstrateGovernor()
state1 = gov.update_pressure(0.91)  # returns self.state
state2 = gov.update_pressure(0.94)  # mutates self.state, returns same ref
assert state2.factor > state1.factor  # FAILS: state1 IS state2
```

The assertion fails because `state1` and `state2` are the same object.

## Solution

Use **separate instances** for each value being compared:

```python
gov1 = SubstrateGovernor()
gov2 = SubstrateGovernor()
state1 = gov1.update_pressure(0.91)
state2 = gov2.update_pressure(0.94)
assert state2.factor > state1.factor  # PASSES: separate objects
```

Or snapshot the value before mutation:

```python
gov = SubstrateGovernor()
factor1 = gov.update_pressure(0.91).factor  # capture primitive, not reference
factor2 = gov.update_pressure(0.94).factor
assert factor2 > factor1  # PASSES: primitives don't alias
```

## Verification

Run the specific test — it should pass after using separate instances.

## References

Python name binding: `state1 = obj.state` binds the name to the object, not a copy.
