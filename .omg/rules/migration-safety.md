---
description: "Prevent breaking database schema and contract migrations"
globs: ["src/cohezion/core/persistence/**", "src/cohezion/data_mesh/**", "src/cohezion/contracts/**"]
alwaysApply: false
---

# Rule: Migration Safety

## Triggers
- Schema modifications in SurrealDB definition files, persistence layers, or Pydantic data contracts.

## Enforced Behavior
1. **Backward Compatibility**: Existing record shapes in `learning`, `kanban_item`, and `model_performance` tables must remain readable.
2. **Non-Destructive DDL**: Never execute `REMOVE TABLE` without explicit user confirmation and automated snapshot.
3. **HTTP Fallback Integrity**: Verify direct HTTP fallback (`_direct_http_upsert`) remains aligned with schema changes.
