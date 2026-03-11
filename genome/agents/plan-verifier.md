---
title: "Agent Card: Plan Verifier"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, agent-card, verification, spec-workflow]
card_type: agent
status: active
agent_type: verification
aspect: knower
neural:
  activation: 0.426
  stage: growing
  cluster: specs
---

# Agent Card: Plan Verifier

> [!abstract] Summary
> The Plan Verifier is a /spec verification agent that validates implementation plans against user requirements. It checks completeness, correctness, and feasibility before the user sees the plan for approval. Runs in parallel with the [[plan-challenger]] agent.

## Identity

| Field | Value |
|-------|-------|
| **Agent** | plan-verifier |
| **Type** | verification |
| **Invocation** | `Agent(subagent_type="plan-verifier")` in spec-plan Step 1.7 |
| **Runtime** | Claude Code subagent (background) |
| **Model** | sonnet (default) |
| **Source** | `.claude/skills/spec-plan/SKILL.md` Step 1.7 |

## Purpose

### What It Does
- Validates that the plan addresses all user requirements from the original /spec prompt
- Checks each task has clear acceptance criteria and file references
- Verifies the plan is implementable within the codebase (files exist, imports valid)
- Flags missing edge cases, error handling, or test coverage

### What It Does NOT Do
- Does not challenge architectural decisions (that's [[plan-challenger]])
- Does not implement code
- Does not modify the plan directly — writes findings to a JSON file

### Success Criteria
- All user requirements mapped to at least one plan task
- No ambiguous or untestable tasks
- All referenced files exist in the codebase

## Triggers

| Trigger | Context | Frequency |
|---------|---------|-----------|
| spec-plan Step 1.7 | Plan draft complete, before user approval | Once per /spec plan |

## Tools Available

| Tool | Purpose | Required |
|------|---------|----------|
| Read | Read plan file and codebase files | Yes |
| Grep | Search codebase for referenced patterns | Yes |
| Glob | Find files referenced in plan tasks | Yes |
| Bash | Run verification commands (tests, type checks) | Yes |

## Input

| Input | Source | Format |
|-------|--------|--------|
| Plan file path | spec-plan orchestrator | File path string |
| Original user prompt | Conversation context | Text |

## Output

| Output | Destination | Format |
|--------|-------------|--------|
| Verification findings | `<session_dir>/plan-verifier.json` | JSON with `must_fix`, `should_fix`, `suggestions` arrays |

## Constraints

> [!warning] Guardrails
> - Read-only: never modifies files
> - Must complete within 5 minutes
> - Writes findings to JSON file, not stdout
> - Runs in background (`run_in_background=true`)

## Interactions

### Collaborates With
- [[plan-challenger]] — Runs in parallel; combined findings reviewed by orchestrator

### Reports To
- spec-plan orchestrator (lead agent)

## Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Completion time | < 5 min | Background execution |
| Finding accuracy | > 90% actionable | Minimize false positives |

## Related

- [[plan-challenger]] — Parallel verification agent
- [[spec-reviewer-compliance]] — Code-phase equivalent
- [[vault-keeper]] — Skill spec for vault maintenance agent

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card |
