---
title: "SheetsBridge MCP Testing Protocol"
date: 2026-02-09
status: completed
tags: [pattern, testing, mcp, sheets-integration, vault-operations]
aspect: thinker
neural:
  activation: 0.83
  stage: mature
  synapse_in: 11
  synapse_out: 10
---

# SheetsBridge MCP Testing Protocol

## Objective

Verify all 5 SheetsBridge MCP tools work end-to-end with live Google Sheet API and proper authentication.

## Test Setup

**Prerequisites**:
- Cloud Vault MCP server running on port 8360
- Google Application Default Credentials (ADC) configured
- Access to Cohezion_Research Google Sheet (ID: `1YcZObTni5L-VnA7O7TIl5ghoy-i3NfXuheFt_oFbmnk`)
- Python 3.11+

**Test Rows**: Rows 95-99 (assumed already processed, safe for testing)

## 5 MCP Tools to Verify

### Tool 1: `sheets_get_all_rows` (Read-only)

**Purpose**: Retrieve all data rows as structured dictionaries

**Test Steps**:
1. Call `sheets_get_all_rows()` via MCP
2. Verify response structure: `[{row, link, status, abstractions, domain, integration_point, vault_note}]`
3. Check: All 84+ papers returned
4. Verify: Columns A-F properly mapped

**Expected Output**:
```json
{
  "row": 2,
  "link": "https://example.com/paper",
  "status": "complete",
  "abstractions": "Key concepts...",
  "domain": "AI/ML",
  "integration_point": "Cohezion concept",
  "vault_note": "paper-filename.md"
}
```

**Auth Verification**:
- ADC token retrieved successfully
- `x-goog-user-project: cohezion-477604` header sent
- No 403/401 errors

---

### Tool 2: `sheets_read_range` (Read-only)

**Purpose**: Read specific A1-notation ranges

**Test Steps**:
1. Call `sheets_read_range("A1:F10")`
2. Verify: Header row + 9 data rows returned
3. Test variations: `"B2:B100"`, `"A1:F1000"` (full sheet)
4. Check: Empty cells handled correctly

**Expected Output**:
```json
[
  ["Link", "Status", "Key Abstractions", "Domain", "Integration Point", "Vault Note"],
  ["https://...", "complete", "...", "AI", "...", "..."],
  ...
]
```

**Auth Verification**:
- A1 notation correctly URL-encoded
- Sheet name (`Sheet1`) prefix handled
- No 404/400 errors

---

### Tool 3: `sheets_update_row` (Write - Single Row)

**Purpose**: Update columns B-E for a specific row

**Test Steps**:
1. Read row 95 current values (save for rollback)
2. Call `sheets_update_row(95, "verified", "Test abstractions", "Testing", "test-integration")`
3. Verify response: `updatedCells=1`, `updatedColumns=4`
4. Read row 95 again to confirm update applied
5. Rollback: Restore original values

**Expected Output**:
```json
{
  "spreadsheetId": "1YcZObTni5L-VnA7O7TIl5ghoy-i3NfXuheFt_oFbmnk",
  "updatedRange": "Sheet1!B95:E95",
  "updatedRows": 1,
  "updatedColumns": 4,
  "updatedCells": 4
}
```

**Auth Verification**:
- Write operation succeeds (not read-only token)
- `valueInputOption=USER_ENTERED` honored
- Data integrity verified

---

### Tool 4: `sheets_batch_update` (Write - Multiple Rows)

**Purpose**: Batch update multiple ranges efficiently

**Test Steps**:
1. Save current values for rows 96-97
2. Prepare batch payload:
   ```json
   [
     {"range": "Sheet1!B96:E96", "values": [["batch_test_1", "abstractions1", "domain1", "integration1"]]},
     {"range": "Sheet1!B97:E97", "values": [["batch_test_2", "abstractions2", "domain2", "integration2"]]}
   ]
   ```
3. Call `sheets_batch_update(data)`
4. Verify: `updatedCells >= 8` (4 cells × 2 rows)
5. Rollback: Restore original values

**Expected Output**:
```json
{
  "spreadsheetId": "1YcZObTni5L-VnA7O7TIl5ghoy-i3NfXuheFt_oFbmnk",
  "totalUpdatedRows": 2,
  "totalUpdatedColumns": 4,
  "totalUpdatedCells": 8,
  "responses": [...]
}
```

**Auth Verification**:
- Multiple updates in single API call
- Rate limit not exceeded
- Atomicity: All rows updated or all fail

---

### Tool 5: `sheets_update_vault_note` (Write - Column F)

**Purpose**: Update column F (Vault Note filename association)

**Test Steps**:
1. Read row 98 current column F value
2. Call `sheets_update_vault_note(98, "test-vault-note.md")`
3. Verify: Single cell update succeeds
4. Read row 98 column F to confirm
5. Rollback: Restore original value

**Expected Output**:
```json
{
  "spreadsheetId": "1YcZObTni5L-VnA7O7TIl5ghoy-i3NfXuheFt_oFbmnk",
  "updatedRange": "Sheet1!F98",
  "updatedRows": 1,
  "updatedColumns": 1,
  "updatedCells": 1
}
```

**Auth Verification**:
- Column F specifically targetable
- `valueInputOption=USER_ENTERED` applied
- No spillover to adjacent columns

---

## Test Execution Checklist

### Pre-Test
- [ ] MCP server running: `ps aux | grep "cloud-vault-mcp"`
- [ ] ADC configured: `gcloud auth application-default print-access-token` succeeds
- [ ] Sheet accessible via browser at: https://sheets.google.com/d/1YcZObTni5L-VnA7O7TIl5ghoy-i3NfXuheFt_oFbmnk

### Test 1: Read-only Verification
- [ ] `sheets_get_all_rows()` returns 84+ rows
- [ ] Columns A-F properly mapped
- [ ] No auth errors (401/403)

### Test 2: Range Read
- [ ] `sheets_read_range("A1:F10")` returns header + 9 rows
- [ ] `sheets_read_range("B2:B100")` returns column B correctly
- [ ] Empty cells handled (not missing, empty strings)

### Test 3: Single Row Update
- [ ] Row 95 read and saved
- [ ] Update succeeds with 4 updated cells
- [ ] Verification read confirms update
- [ ] Rollback restores original values

### Test 4: Batch Update
- [ ] Rows 96-97 saved
- [ ] Batch update succeeds with 8 cells updated
- [ ] Both rows updated correctly
- [ ] Rollback restores both rows

### Test 5: Column F Update
- [ ] Row 98 column F saved
- [ ] Update succeeds with 1 cell updated
- [ ] Verification confirms update
- [ ] Rollback restores original

### Post-Test
- [ ] All test rows (95-99) restored to original state
- [ ] No errors in MCP server logs
- [ ] Sheet API quota not exceeded
- [ ] No data corruption detected

---

## Success Criteria

✅ **All 5 tools tested and working**:
- Read tools: `sheets_get_all_rows`, `sheets_read_range`
- Write tools: `sheets_update_row`, `sheets_batch_update`, `sheets_update_vault_note`

✅ **Auth verified**:
- ADC token retrieval works
- `x-goog-user-project` header included
- No permission errors

✅ **Data integrity**:
- All test rows rolled back to original state
- No unintended side effects
- Sheet remains usable

✅ **Ready for production**:
- All MCP tools verified functional
- Safe to use in automated pipelines
- Rate limits confirmed not exceeded

---

## Troubleshooting

### Error: 401 Unauthorized
**Cause**: ADC token expired or invalid quota project
**Fix**: `gcloud auth application-default login && gcloud config set project cohezion-477604`

### Error: 403 Forbidden
**Cause**: Missing `x-goog-user-project` header or wrong project ID
**Fix**: Verify `quota_project = "cohezion-477604"` in SheetsBridge init

### Error: 404 Not Found
**Cause**: Sheet ID or range notation incorrect
**Fix**: Verify sheet ID `1YcZObTni5L-VnA7O7TIl5ghoy-i3NfXuheFt_oFbmnk` and A1 notation format

### Error: 429 Too Many Requests
**Cause**: Rate limit exceeded
**Fix**: Wait 60 seconds, reduce batch size, or implement exponential backoff

### Write not appearing
**Cause**: `valueInputOption=USER_ENTERED` not applied or sheet auto-refresh disabled
**Fix**: Verify MCP tool uses `valueInputOption=USER_ENTERED` in request body

---

## Test Report Template

```
SheetsBridge MCP Testing - [Date]
=====================================

Test Environment:
- MCP Server: [version] on port 8360
- Python: [version]
- Obsidian Vault: [path]

Results:
- sheets_get_all_rows: ✅ PASS / ❌ FAIL
- sheets_read_range: ✅ PASS / ❌ FAIL
- sheets_update_row: ✅ PASS / ❌ FAIL
- sheets_batch_update: ✅ PASS / ❌ FAIL
- sheets_update_vault_note: ✅ PASS / ❌ FAIL

Auth Verification:
- ADC Token: ✅ PASS / ❌ FAIL
- Quota Header: ✅ PASS / ❌ FAIL
- Permissions: ✅ PASS / ❌ FAIL

Data Integrity:
- Rows 95-99 Rollback: ✅ PASS / ❌ FAIL
- No Corruption: ✅ PASS / ❌ FAIL

Overall Status: ✅ READY FOR PRODUCTION / ❌ BLOCKED

Issues Found: [list any issues]

Next Steps: [recommendations]
```

---

## References

- **SheetsBridge Implementation**: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/sheets_bridge.py`
- **MCP Tool Definitions**: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/server.py` (lines 433-513)
- **Google Sheets API**: https://developers.google.com/sheets/api/reference/rest
- **A1 Notation Guide**: https://developers.google.com/sheets/api/guides/concepts#a1_notation

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan]]
- [[2026-02-09-ollama-mcp-server]]
- [[2026-02-14-settings-files-validation-and-fix]]
- [[2026-02-09-fastmcp-asgi-integration-fix]]
- [[entire-io-to-vault-mapping]]
- [[automated-concept-extraction]]
