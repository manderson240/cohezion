---
type: antigravity-artifact
session_id: 4bda55e4-549b-43bb-88a0-0685989866ac
date: 2026-03-04
title: "Retrospective Phase 17 Surrealdb"
aspect: doer
neural:
  activation: 0.385
  stage: growing
  cluster: Agents
---

# RETROSPECTIVE: Phase 17 - The SurrealDB Mass Ingestion

**Date**: 2026-02-01
**Topic**: Database Corruption, Silent Failures, and Schema Validation
**Phase**: S17 (Production Ingestion)

## 1. The Challenge (Context)
We aimed to ingest a 5.5GB monolithic JSON dataset (`sim_results_25m.json`) containing ~9.3 million records into a local SurrealDB instance. The dataset is complex, containing high-dimensional vectors (`embedding`), variable metadata, and simulation states.

## 2. Issues Encountered

### A. The "Silent Failure" (Client Library)
**Problem**: The Python `surrealdb` client (v1.0.8+) has a method `client.create(table, data)`. When passing a list of dicts for batch insertion, if the operation fails (e.g., due to schema validation), it **does not raise an exception**. Instead, it often returns a string describing the error (e.g., `"Can not use [...] for field..."`).
**Impact**: Our ingestion script saw a non-empty return value and logged `✅ Ingestion complete. Success: 50000`. In reality, **zero** records were inserted.
**Lesson**: Always inspect the *content* and *type* of the return value from the client library, or use raw queries which tend to be more explicit.
**Resolution**: We switched to raw `INSERT INTO ...` queries via `client.query()`.

### B. Strict Schema vs. Real World Data
**Problem**: Our schema defined strict types:
```surql
DEFINE FIELD type ON TABLE universe_nodes TYPE string;
DEFINE FIELD embedding ON TABLE universe_nodes TYPE array<float>;
DEFINE FIELD content ON TABLE universe_nodes TYPE string;
```
However, the source data had records where `type` was missing (null), `content` was null, or `embedding` was null.
**Impact**:
1.  **Rejection**: Records were rejected.
2.  **Corruption**: In a severe twist, repeatedly attempting to force-insert incompatible data into a RocksDB-backed table with strict schema constraints caused a **manifest corruption** in the underlying storage, leading to `Corruption: IO error: No such file or directory` and crashing the server.
**Resolution**:
1.  **Relax Constraints**: We modified the schema to use `FLEXIBLE TYPE option<string>` and `option<array>`. This respects the "Schema-Last" or "Schema-Hybrid" philosophy where we accept the data first and clean it later.
2.  **Clean Slate**: We had to physically delete the `data/` directory and restart the server to recover from the RocksDB corruption.

## 3. The Solution (Pattern 17)

We established a robust pattern for mass ingestion:
1.  **Explode First**: Never ingest varying monolithic files. Always split into uniform JSONL chunks.
2.  **Flexible Schema**: Start with `FLEXIBLE TYPE option<...>` for all potential nullables. Tighten constraints *after* data is landing.
3.  **Raw Queries**: Use parameterized SQL (`INSERT INTO table $param`) rather than helper methods for large batches to ensure visibility into errors.
4.  **Verification Loop**: Run a separate `verify_ingest.py` process that checks `count()` every few seconds. If the count isn't moving, the "Success" logs are lying.

## 4. Metrics & Results
- **Ingestion Rate**: ~23,000 records/second
- **Batch Size**: 50,000 records
- **Concurrency**: 5 Workers
- **Success Rate**: 100% (after fix)

## 5. Next Steps
- **Semantic Caching**: With the data now landing, we can implement the vector search layer.
- **Vacuum**: Once ingestion is done, we might want to tighten the schema back up and delete records that are effectively empty (null content + null type).

> [!IMPORTANT]
> **Key Takeaway**: "Silent Swallowing" of errors in async clients is the enemy of data integrity. Explicit validation of return payloads is mandatory.

## Related Vault Notes

- [[surrealdb]]
