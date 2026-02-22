# /spec - Spec-Driven Development

Structured workflow for implementing features: plan → implement → verify.

## Parse Arguments

```
/spec <task-description>     # Start new workflow
/spec <path/to/plan.md>      # Continue existing plan
/spec --continue <plan.md>   # Resume after session clear
```

## Worktree Question (New Plans Only)

Before planning, ask the user:
```
AskUserQuestion: "Use git worktree isolation for this spec?"
Options: Yes (recommended) / No
```
Pass the choice to spec-plan as `--worktree=yes` or `--worktree=no`.

## Status-Based Dispatch

Read the plan file and dispatch:

| Status | Approved | Action |
|--------|---------|--------|
| PENDING | No | Invoke Skill('spec-plan', args='<plan-path>') |
| PENDING | Yes | Invoke Skill('spec-implement', args='<plan-path>') |
| COMPLETE | * | Invoke Skill('spec-verify', args='<plan-path>') |
| VERIFIED | * | Report completion |

## Context Guard (Before Every Phase Transition)

```bash
cz context --json
```
If percentage >= 80%: hand off instead of starting next phase.

## Context Handoff (90%+)

1. Write continuation file: `cz session status --json` → get session_dir → write `<session_dir>/continuation.md`
2. Trigger clear: `cz session send-clear <plan.md>`

## Rules

1. NO sub-agents except spec verification (plan-verifier, plan-challenger, spec-reviewer-*)
2. NEVER skip verification (Steps 1.7 and 3.0/3.5)
3. Only stopping point: plan approval
4. TDD is mandatory in implementation
5. Update plan checkboxes after EACH task
