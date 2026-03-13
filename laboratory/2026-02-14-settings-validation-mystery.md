---
title: Settings Validation Mystery - /doctor Still Reports 2 Invalid Files
date: 2026-02-14
status: in-progress
tags: [experiment, infrastructure, debug, claude-code, settings-validation]
aspect: thinker
neural:
  activation: 0.84
  stage: mature
  synapse_in: 1
  synapse_out: 13
---

# Settings Validation Mystery: /doctor Still Reports 2 Invalid Files

## Hypothesis

Claude Code's `/doctor` command uses validation rules beyond JSON syntax and tool name matching when checking settings files. Despite both `~/.claude/mcp.json` and `.claude/settings.json` passing JSON validation (jq) and having tool names matching MCP server definitions, `/doctor` still reports "Found 2 invalid settings files." The hypothesis was that `/doctor` applies an internal schema validation that is not publicly documented, or that there exists a third settings file not yet identified.

## Method

1. **Fix #1 — MCP_API_KEY**: Updated `~/.claude/mcp.json` from placeholder value (`"LOAD_FROM_SECURE_ENV_FILE"`) to production bearer token. Verified cloud-vault-mcp authenticates correctly.
2. **Fix #2 — Hook Matchers**: Updated `/home/mike-anderson/vaults/cohezion-vault/.claude/settings.json` to replace 4 empty matchers (`"matcher": ""`) with specific tool matchers (`track_session`, `record_decision`, etc.). Verified all matchers match available MCP server tools.
3. **Validation suite**:
   - Both files pass JSON syntax validation (jq parse successful)
   - All tool names match MCP server definitions
   - Hooks aligned with Phase 2 agent context schema
   - No apparent schema violations in either file
4. Ran `/doctor` again — still reports 2 invalid files

## Results

- **Fixes applied successfully**: Both `mcp.json` and `settings.json` are valid JSON with correct tool references
- **Mystery persists**: `/doctor` still reports 2 invalid settings files despite all verifiable checks passing
- **Possible root causes identified but not confirmed**:
  1. `/doctor` uses an internal schema that differs from JSON syntax + tool name matching (e.g., checking for specific field names, value types, or structure patterns)
  2. A third settings file exists that hasn't been identified (e.g., `settings.local.json` at 421KB may have schema violations)
  3. `/doctor` may have a stale cache that isn't invalidated by file changes
  4. Claude Code may have undocumented schema requirements for settings structure (e.g., required fields, value constraints)

## Analysis

This experiment reveals a gap in Claude Code's observability: the `/doctor` command reports problems but does not provide enough detail to diagnose them. The "2 invalid settings files" message gives no information about:
- Which files are invalid
- What validation rule failed
- What the expected schema is

This creates a debugging dead-end — all externally verifiable checks pass, but the internal validator disagrees.

## Learnings

1. **External validation is insufficient** — JSON syntax validation and tool name matching do not cover Claude Code's full validation surface. There are undocumented schema requirements.
2. **Error messages should be actionable** — "/doctor" reports a problem but provides no path to resolution. An ideal diagnostic would name the file, the field, and the violation.
3. **Large settings files are suspicious** — the 421KB `settings.local.json` likely contains auto-generated or accumulated state that may include schema violations. Size alone suggests it should be investigated.
4. **Debugging opaque systems requires different strategies** — when the validator's rules are unknown, the approach shifts from "fix the known issue" to "binary search for the offending file/field" by removing settings and re-running /doctor.

## Next Steps

- [ ] Try running Claude Code with verbose diagnostics
- [ ] Check if `/doctor` has a verbose or debug mode
- [ ] Inspect Claude Code source for validation logic
- [ ] Check if `settings.local.json` (421KB) has schema violations — reduce by half and test
- [ ] Test if hooks execute without errors
- [ ] Binary search: temporarily rename settings files one at a time to isolate which two files /doctor considers invalid

## Files

- Decision: `decisions/2026-02-14-settings-files-validation-and-fix.md`
- Commit: 18582ce
- Memory: Updated MEMORY.md with Task #11 summary

## Related

- [[2026-02-14-settings-files-validation-and-fix]] — the decision record for the fixes applied
- [[2026-02-09-ollama-mcp-server]] — Ollama MCP server whose tools are referenced in settings
- [[2026-02-12-platform-codification-summary-guide]] — platform codification context
- [[2026-02-10-compound-node-linking-plan]] — plan context for settings changes

## Related Concepts

- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-10-phase-a-implementation-complete]]
- [[runbook-ollama-mcp-operations]]
- [[PRIME_CLAUDE_CODE_PRACTICES]]
- [[troubleshooting-mcp-infrastructure]]
- [[mcp-infrastructure-architecture]]
- [[2026-02-09-ollama-mcp-server-complete]]
- [[2026-02-09-verification-report]]
- [[concept-validation]] — this experiment is fundamentally about validation gaps in tooling infrastructure
