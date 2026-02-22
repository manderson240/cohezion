# /spec-implement - Implementation Phase

Phase 2 of the /spec workflow. Implements every task from an approved plan using TDD.

**Input:** Path to an approved plan file (`Approved: Yes`)
**Output:** All tasks complete, plan status set to COMPLETE
**Next phase:** `Skill(skill='spec-verify', args='<plan-path>')`

---

## Step 2.1: Read Plan and Check State

1. Read the complete plan file
2. Check `git status --short` and `git log --oneline -5`
3. Identify completed tasks (`[x]`) vs. remaining (`[ ]`)

---

## Step 2.1b: Worktree Setup

Check `Worktree:` field in plan header.

**If `Worktree: No`:** Skip this step entirely.

**If `Worktree: Yes`:**

```bash
# Check if worktree already exists (slug = plan filename minus date and .md)
cz worktree detect --json <slug>
```

- **Found:** `cd` to the returned `path`
- **Not found:** `cz worktree create --json <slug>` → `cd` to returned `path`
- **Dirty error:** Ask user: Commit / Stash / Skip worktree isolation

All subsequent steps happen inside the worktree.

---

## Step 2.2: Set Up Task List

```python
TaskList()  # Check for existing tasks from prior session
```

**If tasks exist:** Resume from first `[ ]` task in plan (cross-reference with TaskList).

**If empty:** Create one task per uncompleted plan item:
```python
TaskCreate(subject="Task N: <title>", description="<objective>", activeForm="Implementing <short description>")
```
Set dependencies:
```python
TaskUpdate(taskId="<id>", addBlockedBy=["<dependency-id>"])
```

---

## Step 2.3: TDD Loop (Repeat for Each Task)

**TDD applies to:** functions, modules, CLI commands, hooks, business logic, bug fixes.
**TDD skipped for:** documentation, config files, markdown files.

For each task:

1. `TaskUpdate(taskId, status="in_progress")`
2. Read all files listed in the task's Files section
3. **RED:** Write failing test(s) → verify they fail for the right reason
4. **GREEN:** Write minimal code → verify tests pass
5. **REFACTOR:** Improve if needed, keep tests green
6. Run full test suite: `cd tools/cohezion-engine && uv run pytest -q`
7. Validate every Definition of Done criterion
8. Per-task commit (worktree mode):
   ```bash
   git add <task-files>
   git commit -m "feat(spec): Task N - <short description>"
   ```
9. `TaskUpdate(taskId, status="completed")`
10. Update plan file immediately (Step 2.4)

---

## Step 2.4: Update Plan After EACH Task

**After completing each task, immediately edit the plan:**

```
[ ] Task N: ...  →  [x] Task N: ...
Completed: N-1 | Remaining: M+1  →  Completed: N | Remaining: M
```

Do not proceed to the next task until the checkbox is updated.

---

## Step 2.5: All Tasks Complete → Verification

1. Run full test suite — verify 0 failures
2. Update plan status:
   ```
   Status: PENDING  →  Status: COMPLETE
   ```
3. Register status:
   ```bash
   cz plan register <plan-path> COMPLETE
   ```
4. Check context:
   ```bash
   cz context --json
   ```
   If >= 80%: write continuation file and hand off instead.

5. Invoke verification:
   ```python
   Skill(skill='spec-verify', args='<plan-path>')
   ```

---

## Rules

- TDD is MANDATORY for production code
- NEVER skip tasks (no MVP scope shortcuts)
- Update plan checkboxes after EACH task (not at the end)
- Commits are allowed and expected in worktree mode
- Quality over speed — finish the current task fully before handing off
