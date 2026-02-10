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

## Related Patterns
- [[patterns/troubleshooting-mcp-infrastructure]] - Add telemetry section
- [[patterns/runbook-health-checks]] - Add telemetry file size check
