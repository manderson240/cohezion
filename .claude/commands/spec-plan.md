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
```

Register the plan:
```bash
cz plan register docs/plans/YYYY-MM-DD-<slug>.md PENDING
```

---

## Step 1.2: Explore Codebase

Using Grep, Glob, Read, and `vexor search --mode code`:

1. Find all files relevant to the task
2. Read key files to understand current patterns
3. Identify what exists vs. what needs to be built
4. Note conventions (naming, structure, test patterns, test command)

**Token efficiency:** Use `vexor search` for intent-based discovery. Only read files that are directly relevant. Avoid loading entire directories.

**Do NOT write any code during this phase.**

---

## Step 1.3: Design Implementation

Break the work into 5–12 discrete tasks. For each task:

- Clear objective
- List of files to create/modify/delete (be specific — agents use this list)
- Key decisions and constraints
- Definition of Done (checkable criteria)
- Verify command(s) — must be runnable with no extra setup

**Constraints:**
- Tasks must be ordered by dependency
- Each task must be independently testable
- No task should exceed ~200 lines of production code
- Prefer smaller tasks — 3-5 files max per task

---

## Step 1.4: Write Full Plan

Fill out the plan file with:

```markdown
## Summary
[Goal, architecture, tech stack — 3-5 sentences]

## Runtime Environment
- **project_root:** `<relative path from repo root>`
- **test_command:** `<full command to run tests>`
- **lint_command:** `<full lint command or "none">`
- **type_check_command:** `<full type check command or "none">`
- **install_command:** `<how to install dependencies>`

## Scope
### In Scope
### Out of Scope

## Prerequisites

## Context for Implementer
[Key decisions, constraints, conventions — what a fresh agent needs to resume]

## Progress Tracking
- [ ] Task 1: ...
- [ ] Task 2: ...
**Total Tasks:** N | **Completed:** 0 | **Remaining:** N

## Implementation Tasks
### Task 1: <Title>
**Objective:**
**Dependencies:** None
**Files:**
- Create: `path/to/file.py`
- Modify: `path/to/other.py`
**Key Decisions / Notes:**
**Definition of Done:**
- [ ] criterion 1
- [ ] criterion 2
**Verify:**
```bash
<runnable verify command>
```
...

## Testing Strategy
## Risks and Mitigations
## Open Questions
```

**The `Runtime Environment` section is MANDATORY.** It's how spec-implement and spec-verify know how to run tests without guessing.

---

## Step 1.5: Self-Review

Before running verification agents, check:

- [ ] Every task has specific Files listed
- [ ] Every task has a Definition of Done with checkable criteria
- [ ] Every task has Verify commands that can run without setup
- [ ] Dependencies are correctly ordered
- [ ] No task is vague ("implement X" without specifics)
- [ ] Out of Scope items are explicitly listed
- [ ] Runtime Environment section is complete

Fix any gaps before proceeding.

---

## Step 1.6: Update Worktree Field

If `--worktree=yes` was passed: ensure `Worktree: Yes` in plan header.
If `--worktree=no` was passed: set `Worktree: No`.

---

## Step 1.7: Run Verification Agents (MANDATORY — NEVER SKIP)

**First, resolve the session directory for findings output:**

```bash
SESSION_DIR=$(cz session status --json | python3 -c "import sys,json; print(json.load(sys.stdin)['session_dir'])")
```

Launch both agents in parallel via the Task tool with `run_in_background=true`:

```python
Task(
  subagent_type="general-purpose",
  description="Verify plan completeness",
  prompt=f"""You are a plan verifier. Read the agent instructions at:
  <vault-root>/.claude/agents/plan-verifier.md

  Then read the plan at: <plan-path>

  Focus your review on the Files listed in each task's Files section.
  Write findings JSON to: {SESSION_DIR}/plan-verifier.json""",
  run_in_background=True
)

Task(
  subagent_type="general-purpose",
  description="Challenge plan assumptions",
  prompt=f"""You are a plan challenger. Read the agent instructions at:
  <vault-root>/.claude/agents/plan-challenger.md

  Then read the plan at: <plan-path>

  Write findings JSON to: {SESSION_DIR}/plan-challenger.json""",
  run_in_background=True
)
```

Poll for results using Read tool. Auto-fix all `must_fix` findings before showing the plan to the user.

---

## Step 1.8: Present Plan for Approval

Show the user:

1. Plan summary (goal, task count, Runtime Environment)
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
- ALWAYS resolve session_dir to a real path before Task calls — never pass `<session-id>` as a placeholder
- Runtime Environment section is mandatory in every plan
- Plan file is source of truth — update it continuously
- Batch questions for user — ask once in Step 1.8
