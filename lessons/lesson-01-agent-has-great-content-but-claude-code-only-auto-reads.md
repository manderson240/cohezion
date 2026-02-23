---
title: Agent Output Requires Explicit Reading
date: 2026-02-23
severity: HIGH
category: agent-workflow
tags: [agent-workflow, claude-code, file-reading, operational]
status: validated
---

# Lesson: Agent Output Requires Explicit Reading

## Context

Agents produce output files with rich content. Claude Code in the parent session does not automatically read these files. The content exists but is invisible to the orchestrating session unless explicitly fetched.

## Core Learning

**After spawning agents, you MUST explicitly read their output files. Assume nothing is auto-loaded.**

### Why This Matters
- Agent output is written to disk, not injected into the parent session context
- The parent session has no awareness of what agents produced
- Acting on assumed agent output leads to silent failures or stale data

### Pattern
```python
# WRONG: assume agent output is available in context
run_agent(task)
process(result)  # result not actually in context

# RIGHT: explicitly read agent output file
output_path = run_agent(task)
content = read_file(output_path)
process(content)
```

## Recommendations

### Do
- After every agent task, explicitly read the output file before using results
- Pass the output file path back from agent invocations
- Verify files exist and are non-empty before reading

### Don't
- Assume agent results are in-context after the task completes
- Treat agent task "success" as equivalent to "data available in context"

## Related Concepts

- [[compound-engineering]] - Compound workflows depend on correct inter-agent data flow
- [[agentic-ai]] - Core property of multi-agent orchestration

## Validation

**Discovered**: Feb 2026, during compound engineering sessions
**Status**: Validated across multiple sessions
