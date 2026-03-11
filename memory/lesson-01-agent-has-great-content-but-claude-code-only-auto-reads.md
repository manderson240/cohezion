---
title: Agent Output Requires Explicit Reading
date: 2026-02-23
severity: HIGH
category: agent-workflow
cost_of_forgetting: "Silent data loss -- orchestrating agent acts on empty/stale data while real output sits unread on disk"
tags: [agent-workflow, claude-code, file-reading, operational]
status: validated
aspect: knower
neural:
  activation: 0.524
  stage: growing
  cluster: lessons
---

# Lesson: Agent Output Requires Explicit Reading

## Context

During Cohezion compound engineering sessions, sub-agents were spawned via the Task tool to perform parallel work (code review, research, implementation). These agents write their findings to output files on disk. The parent orchestrating session in Claude Code does not automatically ingest these files into its context. This disconnect caused multiple instances where the orchestrator proceeded as if it had the agent's results, but was actually operating on empty or stale data.

## Problem

The failure mode is subtle and dangerous:

1. **Invisible output**: The agent runs successfully, writes detailed findings to a JSON file, and reports completion. The parent session sees "task completed" but has zero bytes of the actual output in its context.
2. **Assumed availability**: The orchestrator proceeds with processing steps that reference agent results. Since the data was never read, these steps operate on None/empty values, producing silently wrong outcomes.
3. **Late detection**: The error surfaces downstream -- incorrect summaries, missing data in reports, or confusing behavior -- far from the actual root cause (a missing file read).

This pattern was especially dangerous in verification workflows where review agents write structured findings to JSON files. Skipping the read step meant review findings were silently discarded.

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

## Solution

The fix is procedural: treat every agent invocation as a two-step operation: (1) run the agent, (2) read the output. This is now encoded in the workflow enforcement rules:

- Verification agents write findings to session directory JSON files
- The orchestrator polls these files with the Read tool (not TaskOutput, which dumps verbose transcripts)
- Files are checked for existence and non-empty content before processing
- The output path is established before the agent is spawned, so there is no ambiguity about where to read

## Prevention

- **Treat agent output as a file operation**: Just as you would read a database query result, read agent output explicitly
- **Establish output paths before spawning**: Define where agents will write before launching them
- **Validate before processing**: Check that files exist and contain valid data (not empty, not malformed JSON)
- **Never use TaskOutput for verification agents**: It dumps the full verbose transcript into context. Use Read on the structured output file instead.

## Cost of Forgetting

- **Silent data loss**: Agent findings are discarded without any error message
- **Incorrect downstream processing**: Operations that depend on agent output produce wrong results
- **Wasted compute**: The agent did useful work that is simply ignored
- **Debugging difficulty**: The root cause (missing file read) is far from where symptoms appear

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
- [[agent-context]] - Agent output files are the context boundary between parent and child sessions
- [[multi-agent-systems]] - Correct data handoff between agents is foundational to multi-agent reliability
- [[tool-use]] - Reading agent output is a tool operation that must be explicit, not assumed
- [[agent-architecture]] - Architecture must account for the context boundary between orchestrator and sub-agents
- [[non-blocking-observability]] - Verification agent output follows the same read-explicitly pattern as observability data

## Validation

**Discovered**: Feb 2026, during compound engineering sessions
**Status**: Validated across multiple sessions -- now encoded in workflow enforcement rules
