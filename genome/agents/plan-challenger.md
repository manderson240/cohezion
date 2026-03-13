---
title: "Agent Card: Plan Challenger"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, agent-card, verification, spec-workflow]
card_type: agent
status: active
agent_type: verification
aspect: knower
neural:
  activation: 0.67
  stage: growing
  synapse_in: 2
  synapse_out: 3
---

# Agent Card: Plan Challenger

> [!abstract] Summary
> The Plan Challenger is a /spec verification agent that stress-tests implementation plans by questioning assumptions, identifying risks, and proposing alternatives. It acts as an adversarial reviewer to catch blind spots before the user approves the plan. Runs in parallel with the [[plan-verifier]] agent.

## Identity

| Field | Value |
|-------|-------|
| **Agent** | plan-challenger |
| **Type** | verification |
| **Invocation** | `Agent(subagent_type="plan-challenger")` in spec-plan Step 1.7 |
| **Runtime** | Claude Code subagent (background) |
| **Model** | sonnet (default) |
| **Source** | `.claude/skills/spec-plan/SKILL.md` Step 1.7 |

## Purpose

### What It Does
- Questions architectural assumptions in the plan
- Identifies single points of failure, scalability risks, and missing error handling
- Proposes alternative approaches where the plan chose one path without considering others
- Checks for over-engineering or unnecessary complexity

### What It Does NOT Do
- Does not validate requirements coverage (that's [[plan-verifier]])
- Does not implement code
- Does not have veto power — findings are advisory

### Success Criteria
- At least one non-obvious risk or alternative identified
- No "rubber stamp" outputs — if everything looks perfect, dig deeper
- Findings are specific and actionable, not generic warnings

## Triggers

| Trigger | Context | Frequency |
|---------|---------|-----------|
| spec-plan Step 1.7 | Plan draft complete, before user approval | Once per /spec plan |

## Tools Available

| Tool | Purpose | Required |
|------|---------|----------|
| Read | Read plan file and codebase | Yes |
| Grep | Search for patterns and dependencies | Yes |
| Glob | Find related files | Yes |
| WebSearch | Research alternative approaches | Optional |

## Input

| Input | Source | Format |
|-------|--------|--------|
| Plan file path | spec-plan orchestrator | File path string |
| Original user prompt | Conversation context | Text |

## Output

| Output | Destination | Format |
|--------|-------------|--------|
| Challenge findings | `<session_dir>/plan-challenger.json` | JSON with `risks`, `alternatives`, `questions` arrays |

## Constraints

> [!warning] Guardrails
> - Read-only: never modifies files
> - Must complete within 5 minutes
> - Adversarial but constructive — identify risks, don't just criticize
> - Runs in background (`run_in_background=true`)

## Prompt Template

```
You are a plan challenger. Your job is to stress-test this implementation plan
by identifying risks, questioning assumptions, and proposing alternatives.

Be adversarial but constructive. If the plan is solid, dig deeper — there's
always something that could go wrong or be done differently.
```

## Interactions

### Collaborates With
- [[plan-verifier]] — Runs in parallel; combined findings reviewed by orchestrator

### Reports To
- spec-plan orchestrator (lead agent)

## Related

- [[plan-verifier]] — Parallel verification agent
- [[adversarial-review]] — Concept note on adversarial review methodology
- [[spec-reviewer-quality]] — Code-phase equivalent

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card |
