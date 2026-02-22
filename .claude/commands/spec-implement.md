# /spec-implement - Implementation Phase

Phase 2 of the /spec workflow. Implements every task from an approved plan using TDD.

**Input:** Path to an approved plan file (`Approved: Yes`)
**Output:** All tasks complete, plan status set to COMPLETE
**Next phase:** `Skill(skill='spec-verify', args='<plan-path>')`

---

## Step 2.1: Read Plan and Check State

1. Read the complete plan file — note the **Runtime Environment** section for test/lint commands
2. Check `git status --short` and `git log --oneline -5`
3. Clean up stale tasks: `TaskList()` → delete any tasks not relevant to the current plan
4. Identify completed tasks (`[x]`) vs. remaining (`[ ]`)

**Extract from Runtime Environment:**
```
project_root  → where to run commands from
test_command  → e.g. `uv run pytest -q` or `npm test`
lint_command  → e.g. `ruff check .` or `eslint src/`
```

If the plan has no Runtime Environment section, detect it:
- Python: look for `pyproject.toml` → `uv run pytest -q`
- Node: look for `package.json` → `npm test`
- Other: look for `Makefile` → `make test`

---

## Step 2.1b: Worktree Setup

Check `Worktree:` field in plan header.

**If `Worktree: No`:** Skip this step entirely.

**If `Worktree: Yes`:**

```bash
# slug = plan filename minus date prefix and .md extension
cz worktree detect --json <slug>
```

- **Found:** use the returned `path` as working directory for all commands
- **Not found:** `cz worktree create --json <slug>` → use returned `path`
- **Dirty error:** Ask user: Commit / Stash / Skip worktree isolation

All subsequent implementation steps run from the worktree path.

---

## Step 2.2: Set Up Task List

```python
TaskList()  # Check for existing tasks from prior session
```

**If relevant tasks exist (continuation session):** Resume from first uncompleted `[ ]` task.

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
2. Read the files listed in the task's **Files** section (not all changed files)
3. **RED:** Write failing test(s) → run test_command → verify failure is for the right reason
4. **GREEN:** Write minimal code → run test_command → verify tests pass
5. **REFACTOR:** Improve if needed, keep tests green
6. Run full test suite from project_root: `<test_command>`
7. Validate every Definition of Done criterion
8. Per-task commit (worktree mode):
   ```bash
   git add <task-specific-files>
   git commit -m "feat(spec): Task N - <short description>"
   ```
9. `TaskUpdate(taskId, status="completed")`
10. Update plan file immediately (Step 2.4)
11. **Context check** (every 2-3 tasks or after any large task):
    ```bash
    cz context --json
    ```
    - `OK` (< 80%): continue
    - `WARNING` (80-89%): finish current task fully, then hand off
    - `CLEAR_NEEDED` (90%+): see Context Handoff below

---

## Step 2.4: Update Plan After EACH Task

**After completing each task, immediately edit the plan:**

```
[ ] Task N: ...  →  [x] Task N: ...
Completed: N-1 | Remaining: M+1  →  Completed: N | Remaining: M
```

Do not proceed to the next task until the checkbox is updated.

---

## Context Handoff (80%+)

When `cz context --json` returns WARNING or CLEAR_NEEDED:

1. Finish the task currently in progress (do not start new tasks)
2. Run test_command — verify all tests pass
3. Commit any uncommitted work
4. Write continuation file:
   ```bash
   SESSION_DIR=$(cz session status --json | python3 -c "import sys,json; print(json.load(sys.stdin)['session_dir'])")
   ```
   Write `$SESSION_DIR/continuation.md` with:
   - Current plan path and status
   - Last completed task
   - Next task to start
   - Any blockers or decisions pending
5. Trigger clear:
   ```bash
   cz session send-clear <plan-path>
   ```
   If send-clear fails, tell the user: "Context at X%. Run `/clear` and then `/spec <plan-path>`"

**Quality over speed — finish the current task properly, then hand off.**

---

## Step 2.5: All Tasks Complete → Verification

1. Run full test suite from project_root — verify 0 failures
2. Update plan status:
   ```
   Status: PENDING  →  Status: COMPLETE
   ```
3. Register status:
   ```bash
   cz plan register <plan-path> COMPLETE
   ```
4. Context check:
   ```bash
   cz context --json
   ```
   If WARNING or CLEAR_NEEDED: hand off (next session will dispatch to spec-verify).

5. If context OK, invoke verification:
   ```python
   Skill(skill='spec-verify', args='<plan-path>')
   ```

---

## Rules

- TDD is MANDATORY for production code
- NEVER skip tasks (no MVP scope shortcuts)
- Update plan checkboxes after EACH task (not at the end)
- Check context every 2-3 tasks
- Commits are allowed and expected in worktree mode
- Quality over speed — finish the current task fully before handing off
- Read only the files listed in each task's Files section first; expand scope only if needed
