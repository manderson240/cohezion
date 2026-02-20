---
title: Settings Validation Mystery - /doctor Still Reports 2 Invalid Files
date: 2026-02-14
status: in-progress
tags: [infrastructure, debug, claude-code]
---

## Summary

Fixed 2 invalid settings files, verified with jq, confirmed with tools validation — yet `/doctor` still reports "Found 2 invalid settings files".

## What We Fixed

### Fix #1: MCP_API_KEY
- **File**: `~/.claude/mcp.json`
- **Before**: `"MCP_API_KEY": "LOAD_FROM_SECURE_ENV_FILE"` (placeholder)
- **After**: Bearer token set to production key
- **Status**: ✅ Verified — cloud-vault-mcp authenticates correctly

### Fix #2: Hook Matchers
- **File**: `/home/mike-anderson/vaults/cohezion-vault/.claude/settings.json`
- **Before**: 4 empty matchers `"matcher": ""`
- **After**: Specific tool matchers (`track_session`, `record_decision`, etc.)
- **Status**: ✅ Verified — all matchers match available MCP server tools

## Validation Done

✅ Both files valid JSON (jq parse successful)
✅ All tool names match MCP server definitions
✅ Hooks aligned with Phase 2 agent context schema
✅ No apparent schema violations

## The Mystery

`/doctor` still reports 2 invalid files despite all checks passing.

**Possible causes**:
1. `/doctor` uses different validation rules than JSON syntax + tool matching
2. There's a third settings file we haven't identified
3. `/doctor` cache is stale (but files have recent timestamps)
4. Claude Code has schema requirements we can't see

## Next Steps

- [ ] Try running Claude Code with verbose diagnostics
- [ ] Check if `/doctor` has a verbose or debug mode
- [ ] Inspect Claude Code source for validation logic
- [ ] Check if settings.local.json (421KB) has schema violations
- [ ] Test if hooks execute without errors

## Files

- Decision: `decisions/2026-02-14-settings-files-validation-and-fix.md`
- Commit: 18582ce
- Memory: Updated MEMORY.md with Task #11 summary

## Related

- [[2026-02-14-settings-files-validation-and-fix]]
- [[2026-02-09-ollama-mcp-server]]
- [[2026-02-12-platform-codification-summary-guide]]
- [[2026-02-10-compound-node-linking-plan]]
