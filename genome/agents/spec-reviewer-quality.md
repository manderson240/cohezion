---
title: "Agent Card: Spec Reviewer (Quality)"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, agent-card, verification, spec-workflow, code-review]
card_type: agent
status: active
agent_type: verification
aspect: knower
neural:
  activation: 0.66
  stage: growing
  synapse_in: 1
  synapse_out: 3
---

# Agent Card: Spec Reviewer (Quality)

> [!abstract] Summary
> The Quality Reviewer evaluates implemented code for engineering quality — clean architecture, proper error handling, security, performance, and maintainability. It reviews code changes independently of plan compliance, focusing on whether the code is production-worthy. Runs in parallel with [[spec-reviewer-compliance]].

## Identity

| Field | Value |
|-------|-------|
| **Agent** | spec-reviewer-quality |
| **Type** | verification |
| **Invocation** | `Agent(subagent_type="spec-reviewer-quality")` in spec-verify Step 3.0 |
| **Runtime** | Claude Code subagent (background) |
| **Model** | sonnet (default) |
| **Source** | `.claude/skills/spec-verify/SKILL.md` Step 3.0 |

## Purpose

### What It Does
- Reviews all changed files for code quality issues
- Checks for security vulnerabilities (OWASP top 10, injection, XSS)
- Evaluates error handling completeness
- Assesses naming, structure, and readability
- Checks file sizes (>300 lines = must refactor)
- Identifies dead code, unused imports, missing type annotations on public APIs

### What It Does NOT Do
- Does not verify plan compliance (that's [[spec-reviewer-compliance]])
- Does not modify code — writes findings to a JSON file
- Does not evaluate business logic correctness

### Success Criteria
- Zero `must_fix` security issues
- All files under 300 lines (500 hard limit)
- No obvious code smells or anti-patterns

## Triggers

| Trigger | Context | Frequency |
|---------|---------|-----------|
| spec-verify Step 3.0 | Implementation complete (status: COMPLETE) | Once per /spec verify cycle |
| spec-verify Step 3.5 | After fixes from previous findings | On re-verification loops |

## Tools Available

| Tool | Purpose | Required |
|------|---------|----------|
| Read | Read source code, config files | Yes |
| Grep | Find patterns, dead code, unused imports | Yes |
| Glob | Find all changed files | Yes |
| Bash | Run linter, type checker, security scanner | Yes |

## Input

| Input | Source | Format |
|-------|--------|--------|
| Plan file path | spec-verify orchestrator | File path string |
| Changed files list | `cz worktree diff --json <slug>` | JSON array of file paths |

## Output

| Output | Destination | Format |
|--------|-------------|--------|
| Quality findings | `<session_dir>/spec-reviewer-quality.json` | JSON with `must_fix`, `should_fix`, `suggestions` arrays |

## Constraints

> [!warning] Guardrails
> - Read-only: never modifies files
> - Must read every changed file completely (no sampling)
> - Security findings are always `must_fix`
> - File size violations are always `must_fix`
> - Runs in background (`run_in_background=true`)

## Interactions

### Collaborates With
- [[spec-reviewer-compliance]] — Runs in parallel; combined findings drive fix cycle

### Reports To
- spec-verify orchestrator (lead agent)

## Related

- [[plan-challenger]] — Plan-phase quality equivalent
- [[spec-reviewer-compliance]] — Parallel compliance reviewer
- [[ai-safety]] — Security review concepts

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card |
