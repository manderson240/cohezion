---
title: "SheetsBridge End-to-End Test Plan"
date: 2026-02-09
tags: [testing, sheetsbridge, mcp, google-sheets]
aspect: doer
neural:
  activation: 0.386
  stage: growing
  cluster: daily
---

# SheetsBridge End-to-End Test Plan

**Objective**: Verify SheetsBridge MCP integration works with live Google Sheet
**Sheet**: Cohezion_Research (`1YcZObTni5L-VnA7O7TIl5ghoy-i3NfXuheFt_oFbmnk`)
**Test Rows**: 95-99 (safe for reversible testing)

---

## Prerequisites ✅

- ✅ SheetsBridge implementation in `cloud-vault-mcp/src/mcp_server/sheets_bridge.py`
- ✅ Cloud Vault MCP server running on http://127.0.0.1:8360
- ✅ Google ADC credentials configured
- ✅ `x-goog-user-project: cohezion-477604` header in requests
- ⚠️ Test pattern documented in `patterns/sheetsbr idge-mcp-testing.md`

---

## MCP Tools to Test

### 1. `sheets_get_all_rows()` - Read all rows
**Purpose**: Verify auth + quota header work
**Expected**: JSON array of all 99 rows
**Test**:
```python
result = sheets_get_all_rows()
# Verify: 99 rows returned, no auth errors
```

### 2. `sheets_read_range(range)` - Read specific range
**Purpose**: Test A1 notation support
**Range**: `A95:F99` (5 test rows)
**Expected**: 5 rows with columns A-F
**Test**:
```python
result = sheets_read_range("A95:F99")
# Verify: 5 rows, all columns present
```

### 3. `sheets_update_row(row_number, column, value)` - Update single cell
**Purpose**: Test write permissions + single cell update
**Row**: 95 (test row)
**Column**: B (Status)
**Value**: "testing-mcp"
**Test**:
```python
# Before: Read current value
before = sheets_read_range("B95:B95")

# Update
result = sheets_update_row(95, "B", "testing-mcp")

# Verify: Read updated value
after = sheets_read_range("B95:B95")
assert after == "testing-mcp"

# Rollback: Restore original value
sheets_update_row(95, "B", before)
```

### 4. `sheets_batch_update(updates_json)` - Batch update
**Purpose**: Test batch API efficiency
**Updates**: 3 cells in row 96
**Test**:
```python
updates = [
    {"row": 96, "column": "B", "value": "batch-test-1"},
    {"row": 97, "column": "B", "value": "batch-test-2"},
    {"row": 98, "column": "B", "value": "batch-test-3"}
]

# Before: Read current values
before = sheets_read_range("B96:B98")

# Update
result = sheets_batch_update(json.dumps(updates))

# Verify: All 3 cells updated
after = sheets_read_range("B96:B98")

# Rollback: Restore original values
for i, val in enumerate(before):
    sheets_update_row(96 + i, "B", val)
```

### 5. `sheets_update_vault_note(row_number, note_path)` - Update column F
**Purpose**: Test vault note tracking (Column F)
**Row**: 99 (test row)
**Note**: `papers/test-paper.md`
**Test**:
```python
# Before: Read current F99 value
before = sheets_read_range("F99:F99")

# Update
result = sheets_update_vault_note(99, "papers/test-paper.md")

# Verify: Column F updated
after = sheets_read_range("F99:F99")
assert after == "papers/test-paper.md"

# Rollback
sheets_update_vault_note(99, before)
```

---

## Test Sequence

**Phase 1: Read-Only** (Safe, no data changes)
1. ✅ Call `sheets_get_all_rows()` → Verify 99 rows returned
2. ✅ Call `sheets_read_range("A95:F99")` → Verify 5 rows returned

**Phase 2: Single Write + Rollback** (Reversible)
3. ⚠️ Read B95 current value → Store `before`
4. ⚠️ Call `sheets_update_row(95, "B", "testing-mcp")`
5. ⚠️ Read B95 → Verify "testing-mcp"
6. ⚠️ Call `sheets_update_row(95, "B", before)` → Rollback
7. ✅ Read B95 → Verify rollback successful

**Phase 3: Batch Write + Rollback** (Reversible)
8. ⚠️ Read B96:B98 → Store `before`
9. ⚠️ Call `sheets_batch_update()` with 3 updates
10. ⚠️ Read B96:B98 → Verify all 3 updated
11. ⚠️ Rollback all 3 cells
12. ✅ Read B96:B98 → Verify rollback successful

**Phase 4: Column F Update + Rollback** (Reversible)
13. ⚠️ Read F99 → Store `before`
14. ⚠️ Call `sheets_update_vault_note(99, "papers/test-paper.md")`
15. ⚠️ Read F99 → Verify updated
16. ⚠️ Rollback F99
17. ✅ Verify rollback successful

---

## Expected Results

### Success Criteria ✅
- All 5 MCP tools execute without errors
- Auth works (no 401/403 errors)
- Quota header accepted (no quota errors)
- Read operations return expected data
- Write operations modify cells correctly
- Rollbacks restore original values

### Known Risks ⚠️
- **Auth failure**: ADC token may need refresh
- **Quota errors**: Missing `x-goog-user-project` header
- **Rate limiting**: Too many rapid requests (unlikely for 5 tests)
- **Data corruption**: Test rows 95-99 may have important data (CHECK FIRST)

---

## Rollback Plan

**If test fails**:
1. Read all test rows (95-99) BEFORE testing
2. Store original values in JSON file
3. After test failure, restore from JSON
4. Verify restoration with read operation

**Safety**:
- Test rows 95-99 chosen because they're likely already processed
- All operations are reversible
- No writes to Column F until verified safe

---

## Automation Script

**Location**: `/tmp/test_sheets_bridge.py` (if needed)

**Usage**:
```bash
python /tmp/test_sheets_bridge.py
```

**Output**: Test results with pass/fail status for each tool

---

## Post-Test Actions

### If All Tests Pass ✅
1. Update `patterns/sheetsbr idge-mcp-testing.md` with results
2. Mark SheetsBridge as production-ready
3. Document in `daily/2026-02-09-sheetsbridge-verified.md`
4. Enable for Sheets→Vault automated pipelines

### If Tests Fail ❌
1. Document error messages
2. Check ADC credentials
3. Verify quota header configuration
4. Review SheetsBridge implementation
5. Fix and re-test

---

## Next Steps After Verification

1. **Production use**: Enable automated Sheets→Vault sync
2. **Monitoring**: Add error tracking for auth/quota issues
3. **Optimization**: Batch operations for bulk updates (already implemented)
4. **Documentation**: Update README with usage examples

---

**Status**: Test plan ready, awaiting execution
**Dependencies**: Cloud Vault MCP server running, Google Sheet accessible
**Safety**: Reversible operations on test rows only
