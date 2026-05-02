---
name: surrealdb-select-value-subquery
description: |
  Fix for SurrealDB 3.0+ IN subqueries silently returning 0 matches.
  Use when: (1) `WHERE field IN (SELECT col FROM table)` returns 0 rows
  despite data existing, (2) Graph HIHO orphan ratio shows 1.0 with
  thousands of synapses present, (3) any IN clause with a subselect
  produces empty results unexpectedly.
  Key insight: `SELECT col` returns records [{col: "val"}] not scalars.
  Must use `SELECT VALUE col` to get flat array ["val"] for IN to match.
author: Claude Code
version: 1.0.0
---

# SurrealDB SELECT VALUE for Scalar Subqueries

## Problem

`WHERE field IN (SELECT col FROM table)` returns 0 matches in SurrealDB 3.0
even when matching data clearly exists. No error is raised — results are just
silently empty.

## Root Cause

In SurrealDB 3.0, `SELECT col FROM table` returns an array of **records**:
```json
[{"col": "value1"}, {"col": "value2"}]
```

The `IN` operator compares against this array of objects, not against the
string values. No object equals a string, so every row fails the predicate.

## Solution

Use `SELECT VALUE col` to get a **flat array of scalars**:

```sql
-- WRONG: returns [{col: "val1"}, {col: "val2"}]
WHERE path IN (SELECT source FROM synapses)

-- CORRECT: returns ["val1", "val2"]
WHERE path IN (SELECT VALUE source FROM synapses)
```

## Example — Graph HIHO Orphan Ratio

```python
# WRONG: always returns 0, every neuron appears orphaned
connected = await db.query(
    'SELECT count() FROM neurons '
    'WHERE path IN (SELECT source FROM synapses) GROUP ALL'
)

# CORRECT: returns actual connected neuron count
connected = await db.query(
    'SELECT count() FROM neurons '
    'WHERE path IN (SELECT VALUE source FROM synapses) GROUP ALL'
)
```

## Verification

Run the query with a known-populated table. With `SELECT VALUE`, count > 0.
Without it, count = 0 even when data exists.

## Affected Versions

SurrealDB 3.0+. SurrealDB 2.x may behave differently — test before assuming.

## References

- Session 96, Learning L295
- `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` L295
