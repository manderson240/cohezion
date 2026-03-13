---
title: "Agent Card: [Agent Name]"
date: YYYY-MM-DD
version: 1
last_revised: YYYY-MM-DD
tags: [spec, agent-card]
card_type: agent
status: active
agent_type: verification | vault-maintenance | research | implementation
neural:
  activation: 0.39
  stage: growing
  synapse_in: 0
  synapse_out: 3
---

# Agent Card: [Agent Name]

> [!abstract] Summary
> One-paragraph description of the agent's role, when it's invoked, and what outcome it produces.

## Identity

| Field | Value |
|-------|-------|
| **Agent** | [Name] |
| **Type** | verification / vault-maintenance / research / implementation / orchestration |
| **Invocation** | [How it's triggered — skill, subagent_type, hook, manual] |
| **Runtime** | Claude Code subagent / standalone / MCP tool |
| **Model** | [Which model it uses — e.g., sonnet, opus, haiku] |
| **Source** | [Path to agent definition — .claude/skills/, SKILL.md, etc.] |

## Purpose

### What It Does
- [Primary responsibility 1]
- [Primary responsibility 2]

### What It Does NOT Do
- [Explicit scope boundary]

### Success Criteria
- [Measurable outcome 1]
- [Measurable outcome 2]

## Triggers

| Trigger | Context | Frequency |
|---------|---------|-----------|
| [How/when this agent is invoked] | [What must be true] | [How often] |

## Tools Available

| Tool | Purpose | Required |
|------|---------|----------|
| [Tool name] | [What the agent uses it for] | Yes/No |

## Input

| Input | Source | Format |
|-------|--------|--------|
| [What the agent receives] | [Where it comes from] | [Structure] |

## Output

| Output | Destination | Format |
|--------|-------------|--------|
| [What the agent produces] | [Where it goes] | [Structure] |

## Constraints

> [!warning] Guardrails
> These rules the agent MUST follow.

- [Constraint 1 — e.g., "Read-only: never modifies files"]
- [Constraint 2 — e.g., "Must complete within 5 minutes"]
- [Constraint 3 — e.g., "Cannot access external APIs"]

## Prompt Template

```
[Core system prompt or instruction summary — not the full prompt, but the essential behavioral instructions]
```

## Interactions

### Collaborates With
- [[agent-card-name]] — [How they interact]

### Reports To
- [Parent agent or orchestrator]

## Performance

| Metric | Target | Actual |
|--------|--------|--------|
| [Metric name] | [Target value] | [Measured value] |

## Known Limitations

- [Limitation 1]
- [Limitation 2]

## Related

- [[related-skill-spec]]
- [[related-workflow]]

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | YYYY-MM-DD | Initial card |
