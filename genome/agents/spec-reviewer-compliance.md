---
title: "Agent Card: Spec Reviewer (Compliance)"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, agent-card, verification, spec-workflow, code-review]
card_type: agent
status: active
agent_type: verification
aspect: knower
neural:
  activation: 0.67
  stage: growing
  synapse_in: 3
  synapse_out: 3
---

# Agent Card: Spec Reviewer (Compliance)

> [!abstract] Summary
> The Compliance Reviewer validates that implemented code matches the plan specification. It checks every plan task against the actual code changes, verifying acceptance criteria are met, tests exist and pass, and no plan items were skipped or partially implemented. Runs in parallel with [[spec-reviewer-quality]].

## Identity

| Field | Value |
|-------|-------|
| **Agent** | spec-reviewer-compliance |
| **Type** | verification |
| **Invocation** | `Agent(subagent_type="spec-reviewer-compliance")` in spec-verify Step 3.0 |
| **Runtime** | Claude Code subagent (background) |
| **Model** | sonnet (default) |
| **Source** | `.claude/skills/spec-verify/SKILL.md` Step 3.0 |

## Purpose

### What It Does
- Reads the plan file and identifies all tasks with acceptance criteria
- For each task, reads the corresponding code changes and test files
- Verifies tests exist for each behavior described in the plan
- Checks that tests pass (runs the test suite)
- Flags any plan task that was skipped, partially done, or deviates from spec

### What It Does NOT Do
- Does not evaluate code quality (that's [[spec-reviewer-quality]])
- Does not modify code — writes findings to a JSON file
- Does not check non-plan changes (only plan compliance)

### Success Criteria
- Every plan task mapped to corresponding code changes
- Every acceptance criterion verified with evidence
- All tests passing

## Triggers

| Trigger | Context | Frequency |
|---------|---------|-----------|
| spec-verify Step 3.0 | Implementation complete (status: COMPLETE) | Once per /spec verify cycle |
| spec-verify Step 3.5 | After fixes from previous findings | On re-verification loops |

## Tools Available

| Tool | Purpose | Required |
|------|---------|----------|
| Read | Read plan file, source code, test files | Yes |
| Grep | Find implementations of planned features | Yes |
| Glob | Find test files and changed files | Yes |
| Bash | Run tests, type checker, linter | Yes |

## Input

| Input | Source | Format |
|-------|--------|--------|
| Plan file path | spec-verify orchestrator | File path string |
| Changed files list | `cz worktree diff --json <slug>` | JSON array of file paths |

## Output

| Output | Destination | Format |
|--------|-------------|--------|
| Compliance findings | `<session_dir>/spec-reviewer-compliance.json` | JSON with `must_fix`, `should_fix`, `info` arrays |

## Constraints

> [!warning] Guardrails
> - Read-only: never modifies files
> - Must run full test suite and report actual results
> - Findings must reference specific plan task IDs and file:line locations
> - Runs in background (`run_in_background=true`)

## Interactions

### Collaborates With
- [[spec-reviewer-quality]] — Runs in parallel; combined findings drive fix cycle

### Reports To
- spec-verify orchestrator (lead agent)

## Related

- [[plan-verifier]] — Plan-phase equivalent
- [[spec-reviewer-quality]] — Parallel quality reviewer
- [[concept-testing]] — Concept note on testing strategies

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card |
