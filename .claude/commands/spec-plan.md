# /spec-plan - Planning Phase

Phase 1 of the /spec workflow. Explore the codebase, design an implementation plan, run verification agents, and get user approval.

**Input:** Task description (string) or existing plan path (.md file)
**Output:** Approved plan file at `docs/plans/YYYY-MM-DD-<slug>.md`
**Next phase:** `Skill('spec-implement', args='<plan-path>')`

---

## Step 1.1: Initialize Plan File

Create the plan file immediately:

```
docs/plans/YYYY-MM-DD-<slug>.md
```

Write the header block:

```markdown
# <Title>

Created: YYYY-MM-DD
Status: PENDING
Approved: No
Iterations: 0
Worktree: Yes

## Summary
[Goal and architecture — fill in after exploration]
```

Register the plan:
```bash
cz plan register docs/plans/YYYY-MM-DD-<slug>.md PENDING
```

---

## Step 1.2: Explore Codebase

Using Grep, Glob, Read, and `vexor search`:

1. Find all files relevant to the task
2. Read key files to understand current patterns
3. Identify what exists vs. what needs to be built
4. Note conventions (naming, structure, test patterns)

**Do NOT write any code during this phase.**

---

## Step 1.3: Design Implementation

Break the work into 5–12 discrete tasks. For each task:

- Clear objective
- List of files to create/modify/delete
- Key decisions and constraints
- Definition of Done (checkable criteria)
- Verify command(s)

**Constraints:**
- Tasks must be ordered by dependency
- Each task must be independently testable
- No task should exceed ~200 lines of production code

---

## Step 1.4: Write Full Plan

Fill out the plan file with:

```markdown
## Summary
[Goal, architecture, tech stack]

## Scope
### In Scope
### Out of Scope

## Prerequisites

## Context for Implementer
[Key decisions, clean-room constraints, conventions]

## Progress Tracking
- [ ] Task 1: ...
- [ ] Task 2: ...
...
**Total Tasks:** N | **Completed:** 0 | **Remaining:** N

## Implementation Tasks
### Task 1: <Title>
**Objective:**
**Dependencies:** None
**Files:**
**Key Decisions / Notes:**
**Definition of Done:**
**Verify:**
...

## Testing Strategy
## Risks and Mitigations
## Open Questions
```

---

## Step 1.5: Self-Review

Before running verification agents, check:

- [ ] Every task has a Definition of Done
- [ ] Every task has Verify commands
- [ ] Dependencies are correctly ordered
- [ ] No task is vague ("implement X" without specifics)
- [ ] Out of Scope items are explicitly listed
- [ ] Clean-room or license constraints noted if applicable

Fix any gaps before proceeding.

---

## Step 1.6: Update Worktree Field

If `--worktree=yes` was passed: ensure `Worktree: Yes` in plan header.
If `--worktree=no` was passed: set `Worktree: No`.

---

## Step 1.7: Run Verification Agents (MANDATORY — NEVER SKIP)

Launch both agents in parallel via the Task tool with `run_in_background=true`:

```python
Task(
  subagent_type="general-purpose",
  description="Verify plan completeness",
  prompt="You are a plan verifier. Read .claude/agents/plan-verifier.md for your instructions, then read the plan at <plan-path> and execute those instructions. Write findings JSON to ~/.cohezion-engine/sessions/<session-id>/plan-verifier.json",
  run_in_background=True
)

Task(
  subagent_type="general-purpose",
  description="Challenge plan assumptions",
  prompt="You are a plan challenger. Read .claude/agents/plan-challenger.md for your instructions, then read the plan at <plan-path> and execute those instructions. Write findings JSON to ~/.cohezion-engine/sessions/<session-id>/plan-challenger.json",
  run_in_background=True
)
```

Poll for results using Read tool on the output files. Auto-fix all `must_fix` findings before showing the plan to the user.

---

## Step 1.8: Present Plan for Approval

Show the user:

1. Plan summary (goal, task count, key decisions)
2. Any verifier findings that were auto-fixed
3. Open questions (if any)

Ask for approval:
```
AskUserQuestion: "Does this plan look good to proceed with implementation?"
Options: Approve / Request changes
```

**If approved:**
- Set `Approved: Yes` in plan header
- `Skill(skill='spec-implement', args='<plan-path>')`

**If changes requested:**
- Incorporate feedback
- Return to Step 1.5

---

## Rules

- NEVER write code during planning
- NEVER skip Step 1.7 verification agents
- Plan file is source of truth — update it continuously
- Questions → batch them and ask once (Step 1.8)
