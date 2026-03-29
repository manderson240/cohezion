---
name: execute
description: Strict plan execution mode. Reads a plan file, validates preconditions,
  and executes each step sequentially with test gating. Prevents planning drift,
  infrastructure creep, and open-ended exploration. Use when you have an approved
  plan and need disciplined, step-by-step implementation.
arguments:
  - name: plan_path
    description: Path to the plan file (e.g., docs/plans/2026-03-25-add-auth.md). If omitted, uses the most recent plan in docs/plans/.
    required: false
---

# Strict Plan Execution

You are in **execution mode**. Your only job is to implement the plan. No planning, no exploration, no infrastructure unless the plan says so.

## Step 1: Load the Plan

If `$ARGUMENTS` is provided, read that file. Otherwise, find the most recent plan:

```bash
ls -1t docs/plans/*.md 2>/dev/null | head -1
```

Read the plan file. Extract:
- **Tasks**: Each `[ ]` checkbox item
- **Preconditions**: Branch, dependencies, file existence assumptions
- **Acceptance criteria**: How to know each task is done

If no plan is found, STOP and tell the user: "No plan found. Create one with `/spec` or provide a path."

## Step 2: Validate Preconditions

Before writing any code, verify the plan's assumptions still hold:

1. **Git state**: Check current branch matches plan expectations (`git branch --show-current`)
2. **File existence**: Confirm files referenced in the plan exist
3. **Test baseline**: Run `uv run pytest tests/ -q` and record pass/fail counts
4. **Dependencies**: Verify required packages are installed

If preconditions are stale (branch diverged, files renamed, tests regressed):
- Document each discrepancy
- Adapt the plan steps to current reality
- Report adaptations to the user via a brief summary before proceeding

## Step 3: Execute Each Task

For each unchecked `[ ]` task in the plan, in order:

1. **Read** all files you will modify (understand before changing)
2. **Implement** the change described in the task
3. **Test gate**: Run the relevant test suite immediately after the change
   ```bash
   uv run pytest tests/<relevant_module>/ -q
   ```
4. **If tests fail**: Fix the failure before moving to the next task. Max 3 attempts per failure.
5. **If 3 attempts fail**: STOP. Report what you tried, what failed, and suggest the user intervene.
6. **Update the plan file**: Change `[ ]` to `[x]` for completed tasks, update any counts in the plan header.

## Step 4: Milestone Commits

After completing a logical group of tasks (or every 3 tasks, whichever comes first):
- Verify tests still pass with a broader scope: `uv run pytest tests/ -q`
- Stage and describe the changes (do NOT commit without user permission per git-operations rules)
- Suggest a conventional commit message: `feat:`, `fix:`, `refactor:`, etc.

## Step 5: Completion

When all tasks are checked off:
1. Run the full test suite: `uv run pytest tests/ -q`
2. Run linting: `make lint` (if available)
3. Compare test counts: baseline from Step 2 vs. final — report any regressions
4. Update plan status to COMPLETE if all acceptance criteria are met
5. Report: tasks completed, tests passing, files changed

## Hard Rules

These rules are NON-NEGOTIABLE in execution mode:

| Rule | Consequence of Violation |
|------|-------------------------|
| No new infrastructure, frameworks, or dependencies unless explicitly in the plan | Revert and re-read the plan |
| No entering plan mode, no `/spec`, no "let me think about the architecture" | You already have a plan. Execute it. |
| No open-ended exploration or research tangents | If you need info, use targeted Grep/Read, not broad exploration |
| Max 3 iterations per approach before pivoting | If approach A fails 3 times, try approach B or escalate |
| Test after every code change | No batching changes without verification |
| Read before modifying | Never edit a file you haven't read in this session |
| One task at a time | Complete and verify before starting the next |

## Recovery

If you get stuck:
1. Re-read the plan task description — are you solving the right problem?
2. Check if a simpler approach exists (YAGNI)
3. Search for working patterns in the codebase (`Grep` for similar implementations)
4. After 3 failed attempts: escalate to user with concrete details of what failed and why

## Anti-Patterns

- "Let me first set up a utility module for..." — NO. Implement inline, extract later if needed.
- "We should also consider..." — NO. The plan is the scope. Nothing more.
- "Before we start, let me research..." — NO. You have the plan. Start executing.
- Committing broken code to "save progress" — NO. Tests must pass.
- Skipping test gates because "this is a simple change" — NO. Every change gets tested.
