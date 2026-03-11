---
date: "{{date}}"
title: "Agent Execution Summary - {{session_id}}"
tags: [agent, execution, entire.io]
status: archived
source: entire.io
session_id: "{{session_id}}"
agent_names: {{agent_names}}
---

## Execution Summary

**Duration**: {{duration_ms}}ms
**Status**: {{status}} (completed | error | running)
**Model**: {{model_used}} (haiku | sonnet | opus)
**Turns**: {{total_turns}}
**Functions**: {{total_functions}}

## Key Decisions

{{#decisions}}
- [[{{decision_title}}]] - {{decision_reasoning}}
{{/decisions}}

## Context Shifts

{{#context_shifts}}
- {{context_shift}}
{{/context_shifts}}

## Extracted Learnings

{{#learnings}}
- [[{{lesson_title}}]] - Severity: {{severity}} {{#auto_extracted}}(auto-extracted){{/auto_extracted}}
{{/learnings}}

## Session Artifacts

{{#vault_notes_created}}
- [[{{note_path}}]]
{{/vault_notes_created}}

## Related Research

{{#papers_referenced}}
- [[{{paper_title}}]] - {{paper_context}}
{{/papers_referenced}}

## Metrics & Performance

```json
{
  "total_turns": {{total_turns}},
  "total_functions": {{total_functions}},
  "errors": {{error_count}},
  "recovery_attempts": {{recovery_attempts}}
}
```

## Session ID

`{{session_id}}`
