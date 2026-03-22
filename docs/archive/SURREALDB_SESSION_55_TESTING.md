# Session 55 SurrealDB Testing Procedure

## Overview

This document provides step-by-step procedures to validate the Session 55 schema and queries before production use in Phases C-D.

---

## Pre-Testing Setup

### 1. Verify SurrealDB Service

```bash
# Check if SurrealDB is running
ps aux | grep surreal

# If not running, start it
surreal start --log debug --user root --pass root file://data/cohezion.db &

# Verify connectivity
surreal sql --endpoint ws://localhost:8000 \
  --user root --pass root \
  --namespace cohezion --database core \
  --query "SELECT * FROM information::tables"
```

### 2. Create Test Namespace and Database

```bash
# Connect to root namespace
surreal sql --endpoint ws://localhost:8000 \
  --user root --pass root

# Run in SurrealDB console:
# CREATE NAMESPACE cohezion;
# CREATE DATABASE core;
# USE NAMESPACE cohezion;
# USE DATABASE core;
```

---

## Test Suite 1: Schema Creation

### Test 1.1: Create Session Metadata Table

**Procedure**:
```bash
surreal sql --endpoint ws://localhost:8000 \
  --user root --pass root \
  --namespace cohezion --database core \
  --file SURREALDB_SESSION_55_SCHEMA.md
```

**Expected Result**:
- All 6 tables created successfully
- All indexes created without errors
- No schema conflicts or validation errors

**Verification Query**:
```surql
SELECT * FROM information::tables
WHERE name CONTAINS "session_55"
ORDER BY name;
```

**Expected Output**:
```
name                              | engine
──────────────────────────────────┼────────
session_55_actions                | kvs
session_55_cleanup_journey        | kvs
session_55_decisions              | kvs
session_55_entire_io              | kvs
session_55_errors                 | kvs
session_55_file_manifest          | kvs
action_justifies_decision         | kvs
error_resolved_by_action          | kvs
file_removed_by_action            | kvs
```

### Test 1.2: Verify Field Definitions

**Procedure**:
```surql
SELECT type FROM information::fields
WHERE table = "session_55_cleanup_journey"
ORDER BY name;
```

**Expected Result**:
- All required fields present (session_id, phase, status, etc.)
- Field types correct (string, int, float, datetime, array)
- UNIQUE constraints on session_id

---

## Test Suite 2: Insert and Update Operations

### Test 2.1: Insert Session Record

**Procedure**:
```surql
CREATE session_55_cleanup_journey SET
  session_id = "55-test-session",
  phase = "PHASE_B",
  status = "planned",
  title = "Test Session 55",
  team_members = ["test-specialist"],
  lead_specialist = "test-specialist",
  approval_status = "pending",
  completion_percentage = 0.0,
  total_actions_planned = 10,
  total_actions_completed = 0,
  total_actions_failed = 0;
```

**Expected Result**:
- Record created successfully
- Record ID returned (e.g., `session_55_cleanup_journey:abc123`)
- Timestamp auto-set to current time

**Verification**:
```surql
SELECT * FROM session_55_cleanup_journey
WHERE session_id = "55-test-session";
```

### Test 2.2: Insert Action Record (Success Case)

**Procedure**:
```surql
CREATE session_55_actions SET
  action_id = "test-action-001",
  action_type = "backup-created",
  phase = "PHASE_B",
  specialist = "test-specialist",
  result = "success",
  severity = "low",
  description = "Test backup creation",
  details = {
    test: true,
    files: 100,
    size: 1000000
  },
  tokens_used = 100;
```

**Expected Result**:
- Record created with valid IDs
- All required fields present
- Timestamp defaults applied

### Test 2.3: Insert Action with Error

**Procedure**:
```surql
CREATE session_55_actions SET
  action_id = "test-action-fail-001",
  action_type = "file-removed",
  phase = "PHASE_C",
  specialist = "test-specialist",
  result = "failure",
  severity = "high",
  error_message = "Test error: permission denied",
  recovery_attempted = true,
  retry_count = 2;
```

**Expected Result**:
- Record created with error fields populated
- Recovery fields accessible

### Test 2.4: Bulk Insert Actions

**Procedure**:
```surql
CREATE session_55_actions [
  {
    action_id: "bulk-001",
    action_type: "cleanup-started",
    phase: "PHASE_C",
    specialist: "test-specialist",
    result: "success",
    tokens_used: 50
  },
  {
    action_id: "bulk-002",
    action_type: "cleanup-started",
    phase: "PHASE_C",
    specialist: "test-specialist",
    result: "success",
    tokens_used: 75
  },
  {
    action_id: "bulk-003",
    action_type: "cleanup-started",
    phase: "PHASE_C",
    specialist: "test-specialist",
    result: "success",
    tokens_used: 60
  }
];
```

**Expected Result**:
- All 3 records created successfully
- Array response with 3 records

### Test 2.5: Update Action Status

**Procedure**:
```surql
UPDATE session_55_actions
  SET result = "success", duration_seconds = 120, completed_at = time::now()
WHERE action_id = "test-action-fail-001";
```

**Expected Result**:
- Record updated successfully
- Old values replaced

**Verification**:
```surql
SELECT result, duration_seconds FROM session_55_actions
WHERE action_id = "test-action-fail-001";
```

### Test 2.6: Update Session Progress

**Procedure**:
```surql
UPDATE session_55_cleanup_journey
  SET
    status = "in_progress",
    total_actions_completed = 5,
    completion_percentage = 50.0
WHERE session_id = "55-test-session";
```

**Expected Result**:
- Session record updated
- Progress fields updated correctly

---

## Test Suite 3: Query Operations

### Test 3.1: Query by Index (Phase)

**Procedure**:
```surql
SELECT * FROM session_55_actions
WHERE phase = "PHASE_C"
LIMIT 10;
```

**Expected Result**:
- Query returns results quickly (index used)
- Only records with phase = "PHASE_C" returned

**Performance**: Should complete in <100ms

### Test 3.2: Query by Result Status

**Procedure**:
```surql
SELECT action_id, action_type, result FROM session_55_actions
WHERE result = "failure"
ORDER BY severity DESC;
```

**Expected Result**:
- All failure records returned
- Ordered by severity

### Test 3.3: Aggregate Query (Count by Type)

**Procedure**:
```surql
SELECT action_type, COUNT(action_id) as count,
       SUM(tokens_used) as total_tokens,
       SUM(duration_seconds) as total_duration
FROM session_55_actions
GROUP BY action_type;
```

**Expected Result**:
- Grouped results with aggregates
- Total tokens and duration calculated correctly

### Test 3.4: Time Range Query

**Procedure**:
```surql
SELECT * FROM session_55_actions
WHERE started_at > time::now() - 1h
  AND started_at < time::now()
ORDER BY started_at DESC;
```

**Expected Result**:
- Records from last hour returned
- Ordered by timestamp descending

### Test 3.5: Complex Nested Query

**Procedure**:
```surql
SELECT
  session_id,
  (SELECT COUNT() FROM session_55_actions WHERE phase = "PHASE_C") as phase_c_actions,
  (SELECT COUNT(WHERE result = "success") FROM session_55_actions) as successful_actions,
  (SELECT SUM(tokens_used) FROM session_55_actions) as total_tokens
FROM session_55_cleanup_journey
WHERE session_id = "55-test-session";
```

**Expected Result**:
- Session metadata with action counts and totals
- Nested counts accurate

---

## Test Suite 4: Relationship Operations

### Test 4.1: Create Graph Edge (Action to Decision)

**Procedure**:
```surql
-- First create test decision
CREATE session_55_decisions SET
  decision_id = "test-decision-001",
  decision_text = "Test decision",
  category = "cleanup-strategy",
  options_considered = ["option-a", "option-b"],
  rationale = "Testing",
  approver = "test-specialist",
  approval_status = "approved";

-- Then link action to decision
CREATE action_justifies_decision SET
  action_id = (SELECT id FROM session_55_actions WHERE action_id = "test-action-001"),
  decision_id = (SELECT id FROM session_55_decisions WHERE decision_id = "test-decision-001"),
  relationship_type = "implementation_of";
```

**Expected Result**:
- Edge created successfully
- Both related records exist

### Test 4.2: Query Graph Relationships

**Procedure**:
```surql
SELECT
  (SELECT {id, action_type} FROM action_id.action_id).action_type as action,
  (SELECT {id, decision_text} FROM decision_id.decision_id).decision_text as decision
FROM action_justifies_decision
WHERE relationship_type = "implementation_of";
```

**Expected Result**:
- Graph edges returned with joined data

---

## Test Suite 5: Error Handling

### Test 5.1: Invalid Phase Value

**Procedure**:
```surql
CREATE session_55_actions SET
  action_id = "invalid-phase",
  action_type = "test",
  phase = "INVALID_PHASE",  -- Should fail validation
  specialist = "test",
  result = "success";
```

**Expected Result**:
- Error returned (schema validation fails)
- Record not created

### Test 5.2: Missing Required Fields

**Procedure**:
```surql
CREATE session_55_actions SET
  action_id = "missing-fields"
  -- Missing required fields: action_type, phase, specialist, result
;
```

**Expected Result**:
- Error returned
- Record not created

### Test 5.3: Duplicate Session ID (UNIQUE Constraint)

**Procedure**:
```surql
-- First create original
CREATE session_55_cleanup_journey SET
  session_id = "55-unique-test",
  phase = "PHASE_B",
  status = "planned";

-- Try to create duplicate
CREATE session_55_cleanup_journey SET
  session_id = "55-unique-test",
  phase = "PHASE_B",
  status = "planned";
```

**Expected Result**:
- Second insert fails (UNIQUE constraint violation)
- First record remains intact

### Test 5.4: Invalid Field Types

**Procedure**:
```surql
CREATE session_55_actions SET
  action_id = "type-error",
  action_type = "test",
  phase = "PHASE_B",
  specialist = "test",
  result = "success",
  tokens_used = "not_a_number";  -- Should be int
```

**Expected Result**:
- Error returned (type mismatch)
- Record not created

---

## Test Suite 6: Entire.io Integration

### Test 6.1: Create Entire.io Checkpoint

**Procedure**:
```surql
CREATE session_55_entire_io SET
  checkpoint_id = "entire-io-test",
  phase = "PHASE_B",
  metadata_captured = true,
  metadata_checksum = "test_checksum_abc123",
  journey_data_readable = true,
  validation_passed = true,
  entire_io_status = "online";
```

**Expected Result**:
- Checkpoint created successfully
- All fields accessible

### Test 6.2: Verify Entire.io State

**Procedure**:
```surql
SELECT checkpoint_id, phase, metadata_captured, journey_data_readable,
       validation_passed, entire_io_status
FROM session_55_entire_io
WHERE checkpoint_id = "entire-io-test";
```

**Expected Result**:
- Record returned with all fields populated

---

## Test Suite 7: File Manifest Operations

### Test 7.1: Add Files to Manifest

**Procedure**:
```surql
CREATE session_55_file_manifest [
  {
    file_id: "file-001",
    file_path: "/test/cache/file1.json",
    phase_removed: "PHASE_C",
    file_size_bytes: 1000000,
    file_type: "cache",
    action_taken: "removed",
    bytes_freed: 1000000
  },
  {
    file_id: "file-002",
    file_path: "/test/logs/log.txt",
    phase_removed: "PHASE_C",
    file_size_bytes: 500000,
    file_type: "log",
    action_taken: "compressed",
    compressed_size_bytes: 50000,
    bytes_freed: 450000
  }
];
```

**Expected Result**:
- 2 files added to manifest
- IDs returned

### Test 7.2: File Recovery Status

**Procedure**:
```surql
SELECT file_path, action_taken, recovery_possible, recovery_location
FROM session_55_file_manifest
WHERE recovery_possible = true;
```

**Expected Result**:
- Files marked as recoverable returned
- Recovery locations shown

---

## Test Suite 8: Performance & Scalability

### Test 8.1: Insert 100 Actions

**Procedure**:
```bash
cat > bulk_insert.surql << 'EOF'
CREATE session_55_actions [
  { action_id: "perf-001", action_type: "test", phase: "PHASE_C", specialist: "test", result: "success" },
  { action_id: "perf-002", action_type: "test", phase: "PHASE_C", specialist: "test", result: "success" },
  -- ... 98 more records
];
EOF

time surreal sql --endpoint ws://localhost:8000 \
  --user root --pass root \
  --namespace cohezion --database core \
  --file bulk_insert.surql
```

**Expected Result**:
- All 100 records inserted
- Completion time: <1 second

### Test 8.2: Query 100K Records

**Procedure**:
```bash
# Generate large dataset (if needed)
time surreal sql --endpoint ws://localhost:8000 \
  --user root --pass root \
  --namespace cohezion --database core \
  --query "SELECT COUNT() FROM session_55_actions"
```

**Expected Result**:
- Query completes in <500ms
- Count returned accurately

### Test 8.3: Aggregation Performance

**Procedure**:
```bash
time surreal sql --endpoint ws://localhost:8000 \
  --user root --pass root \
  --namespace cohezion --database core \
  --query "
    SELECT phase, COUNT() as count, SUM(tokens_used) as tokens
    FROM session_55_actions
    GROUP BY phase
  "
```

**Expected Result**:
- Grouped aggregation returns in <500ms
- Correct totals per phase

---

## Test Suite 9: Cleanup & Teardown

### Test 9.1: Delete Test Records

**Procedure**:
```surql
DELETE FROM session_55_cleanup_journey WHERE session_id = "55-test-session";
DELETE FROM session_55_actions WHERE action_id CONTAINS "test-" OR action_id CONTAINS "perf-";
DELETE FROM session_55_decisions WHERE decision_id = "test-decision-001";
DELETE FROM session_55_entire_io WHERE checkpoint_id = "entire-io-test";
DELETE FROM session_55_file_manifest WHERE file_id CONTAINS "file-";
DELETE FROM session_55_errors WHERE error_id CONTAINS "test-";
```

**Expected Result**:
- All test records deleted
- No cascade errors

### Test 9.2: Verify Clean State

**Procedure**:
```surql
SELECT COUNT() FROM session_55_cleanup_journey WHERE session_id CONTAINS "test-" OR session_id CONTAINS "55-test";
SELECT COUNT() FROM session_55_actions WHERE action_id CONTAINS "test-" OR action_id CONTAINS "perf-";
```

**Expected Result**:
- 0 records in all test-related queries
- Database ready for production use

---

## Automation Script: Run All Tests

```bash
#!/bin/bash

# test_session_55_schema.sh

ENDPOINT="ws://localhost:8000"
USER="root"
PASS="root"
NAMESPACE="cohezion"
DATABASE="core"

echo "=== Test Suite 1: Schema Creation ==="
surreal sql --endpoint $ENDPOINT --user $USER --pass $PASS \
  --namespace $NAMESPACE --database $DATABASE \
  --file SURREALDB_SESSION_55_SCHEMA.md

echo "=== Test Suite 2: Insert Operations ==="
surreal sql --endpoint $ENDPOINT --user $USER --pass $PASS \
  --namespace $NAMESPACE --database $DATABASE \
  --query "
    CREATE session_55_cleanup_journey SET
      session_id = 'test-auto-001',
      phase = 'PHASE_B',
      status = 'planned',
      title = 'Auto Test';
  "

echo "=== Test Suite 3: Queries ==="
surreal sql --endpoint $ENDPOINT --user $USER --pass $PASS \
  --namespace $NAMESPACE --database $DATABASE \
  --query "
    SELECT * FROM session_55_cleanup_journey
    WHERE session_id = 'test-auto-001';
  "

echo "=== Test Suite 9: Cleanup ==="
surreal sql --endpoint $ENDPOINT --user $USER --pass $PASS \
  --namespace $NAMESPACE --database $DATABASE \
  --query "
    DELETE FROM session_55_cleanup_journey WHERE session_id = 'test-auto-001';
  "

echo "=== All Tests Complete ==="
```

Run it:
```bash
chmod +x test_session_55_schema.sh
./test_session_55_schema.sh
```

---

## Success Criteria Checklist

- [ ] All 6 tables created successfully
- [ ] All indexes created and functional
- [ ] Insert operations work (single and bulk)
- [ ] Update operations work
- [ ] Query operations complete in <500ms
- [ ] Aggregation queries return correct results
- [ ] Graph relationships functional
- [ ] Error handling validates data
- [ ] UNIQUE constraints enforced
- [ ] Entire.io checkpoint system operational
- [ ] File manifest tracks files correctly
- [ ] Recovery locations accessible
- [ ] Cleanup script removes test data
- [ ] Database ready for Phase C execution

---

## Troubleshooting

### Issue: Connection timeout
**Solution**: Verify SurrealDB running with `ps aux | grep surreal`

### Issue: Authentication failed
**Solution**: Check credentials in connection string

### Issue: Table not found
**Solution**: Verify namespace and database selected (`USE NAMESPACE cohezion; USE DATABASE core;`)

### Issue: Field type error
**Solution**: Check field definitions in SURREALDB_SESSION_55_SCHEMA.md

### Issue: Performance slow
**Solution**: Verify indexes created with `SELECT * FROM information::indexes`

---

## Next Steps

After all tests pass:
1. Commit schema files to git
2. Backup SurrealDB database
3. Ready for Phase C execution
4. Monitor performance with real actions
5. Adjust indexes if needed

