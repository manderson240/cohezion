---
title: Telemetry Corruption Fix
date: 2026-02-10
tags: [retrospective, troubleshooting, claude-code]
status: complete
duration: 5 minutes
---

# Telemetry Corruption Fix

## Problem
Claude Code reported "2 invalid setting files" causing internal issues.

## Diagnosis
- Located 2 corrupted JSONL files in `~/.claude/telemetry/`
- Combined size: 8MB (7.9MB + 154KB)
- Files accumulated failed telemetry events over time

## Fix
```bash
rm ~/.claude/telemetry/1p_failed_events.*.json
```

## Result
- ✅ 0 invalid configs remaining
- ✅ 8MB disk space freed
- ✅ Claude Code runs clean

## Root Cause
Telemetry JSONL files grew indefinitely when events failed to send to Anthropic servers. No rotation/cleanup mechanism.

## Lessons
1. **JSONL ≠ JSON**: Files named `.json` can be JSONL format (newline-delimited)
2. **Telemetry is disposable**: Safe to delete failed event logs
3. **Size signals corruption**: 7.9MB telemetry file = accumulation problem

## Prevention
Add to maintenance runbook:
```bash
# Check telemetry file sizes monthly
du -sh ~/.claude/telemetry/*.json

# Clean if > 1MB
find ~/.claude/telemetry -name "*.json" -size +1M -delete
```

## Follow-Up: Debug Log Bloat Discovery

After fixing telemetry, discovered **1.6GB debug log accumulation** (see [[2026-02-10-debug-log-bloat-analysis]]).

**Root Causes**:
1. **Mailbox Polling Storm**: 734,658 polling calls → 474MB log
2. **MCP Connection Spam**: 5,264 failed retries → 728MB logs
3. **ZodError Accumulation**: 329 validation errors → 55MB log

**Cleanup Results**:
- Deleted 16 logs >10MB (1.5GB total)
- Freed: 262MB debug/, 297MB total
- Before: 300MB → After: 38MB (87% reduction)
- Preserved: 112 recent small logs for debugging

**Lessons Extracted**:
- [[2026-02-10-debug-log-bloat-analysis]] - Complete forensic analysis
- [[log-rotation-and-monitoring]] - Prevention pattern

## Related Patterns
- [[troubleshooting-mcp-infrastructure]] - Add telemetry section
- [[runbook-health-checks]] - Add telemetry + debug log size checks
- [[log-rotation-and-monitoring]] - Automated log rotation
- [[2026-02-10-debug-log-bloat-analysis]] - Debug log forensics

## Related Concepts

- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-14-phases-1-3-retrospective-key-learnings]]
- [[2026-02-09-ollama-mcp-server]]
- [[2026-02-14-session-60-retrospective-revised-plan]]
- [[2026-02-14-compound-engineering-team-execution-retrospective]]
- [[2026-02-12-platform-codification-summary-guide]]
- [[2026-02-13-session-60-retrospective-and-revised-plan]]
- [[2026-02-14-graphrag-verification-and-integration-session]]
