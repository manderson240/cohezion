# /spec-verify - Verification Phase

Phase 3 of the /spec workflow. Runs tests, code review agents, and confirms all plan criteria are met.

**Input:** Path to a COMPLETE plan file
**Output:** Plan status set to VERIFIED (or PENDING with fix tasks added)
**Loop:** If issues found → fix tasks added → `Skill('spec-implement')` → re-verify

---

## Step 3.0: Pre-Verification Setup

1. Read the plan file — confirm `Status: COMPLETE`
2. Extract from **Runtime Environment** section:
   - `project_root` — where to run commands from
   - `test_command` — how to run tests
   - `lint_command` — how to lint (skip if "none")
   - `type_check_command` — how to type-check (skip if "none")
3. Run test_command from project_root — all must pass before code review agents run
4. Resolve session directory for findings output:
   ```bash
   SESSION_DIR=$(cz session status --json | python3 -c "import sys,json; print(json.load(sys.stdin)['session_dir'])")
   ```
5. Get changed files:
   ```bash
   git diff --name-only HEAD~N..HEAD  # N = number of commits in this spec branch
   ```

---

## Step 3.1: Launch Code Review Agents (MANDATORY — NEVER SKIP)

**Launch immediately** — agents work in parallel while you run lint/type checks.

Resolve all paths before constructing prompts. Never pass `<session-id>` as a placeholder.

```python
Task(
  subagent_type="general-purpose",
  description="Compliance review",
  prompt=f"""You are a compliance reviewer.
  Read agent instructions: <absolute-path>/.claude/agents/spec-reviewer-compliance.md
  Read plan: <absolute-plan-path>

  Files to review (from plan's Files sections — read these first):
  <list files from each task's Files section>

  Expand to other changed files only if needed for integration checks.
  Write findings JSON to: {SESSION_DIR}/findings-compliance.json""",
  run_in_background=True
)

Task(
  subagent_type="general-purpose",
  description="Quality review",
  prompt=f"""You are a quality reviewer.
  Read agent instructions: <absolute-path>/.claude/agents/spec-reviewer-quality.md
  Read plan: <absolute-plan-path>

  Production files to review (non-test files from plan's Files sections):
  <list production files from plan>

  Test files to review:
  <list test files from plan>

  Write findings JSON to: {SESSION_DIR}/findings-quality.json""",
  run_in_background=True
)
```

---

## Step 3.2: Run Linting and Type Checks

While agents work in background, run mechanical checks from project_root:

```bash
# Lint (if not "none")
<lint_command>

# Type check (if not "none")
<type_check_command>
```

Fix all errors immediately. Warnings are acceptable; errors are blockers.

**File length check — all production files:**
```bash
wc -l <production files> | sort -n | tail -20
```
- > 300 lines: warning, refactor if time allows
- > 500 lines: must_fix, split before marking complete

---

## Step 3.3: Collect Agent Findings

Poll for results by reading the findings files (do not use TaskOutput):

```python
Read(f"{SESSION_DIR}/findings-compliance.json")
Read(f"{SESSION_DIR}/findings-quality.json")
```

Retry every 15-30 seconds if not ready. If still missing after 3 attempts, re-launch that agent synchronously (without `run_in_background`).

**Fix all findings automatically — no user confirmation needed:**

1. **must_fix** findings: fix immediately, re-run test_command after each
2. **should_fix** findings: fix immediately
3. **suggestions**: implement if quick and low-risk

**NEVER ask "Should I fix these?"**

---

## Step 3.4: Definition of Done Audit

For each task in the plan, validate every DoD criterion:

```markdown
Task N: <title>
- [ ] criterion 1 → [evidence: command output or code reference]
- [ ] criterion 2 → [evidence]
```

Run each task's Verify commands. If a criterion is unmet:
- Fixable inline → fix immediately
- Requires significant work → add task to plan, set Status: PENDING, increment Iterations, loop back

---

## Step 3.5: Re-Verification Loop (if fixes applied)

If any code changed in Steps 3.2-3.4:

1. Re-run test_command
2. Re-run both review agents (same prompts, same output paths — agents overwrite)
3. Collect and process findings
4. Repeat until both agents return zero must_fix and zero should_fix

Maximum 3 iterations. If issues persist after 3 loops, add them as tasks in the plan.

---

## Step 3.6: Worktree Sync (Conditional)

**Only when `Worktree: Yes` in plan header.**

Get diff:
```bash
cz worktree diff --json <slug>
```

Ask user for sync decision:
```
AskUserQuestion: "Sync worktree changes to base branch?"
Options:
  - Merge and clean up (squash merge + delete worktree)
  - Keep worktree (sync manually later)
  - Discard changes
```

**If approved:**
```bash
cz worktree sync --json <slug>
cz worktree cleanup --json <slug>
```

---

## Step 3.7: Mark VERIFIED

Update plan file:
```
Status: COMPLETE  →  Status: VERIFIED
```

Register:
```bash
cz plan register <plan-path> VERIFIED
```

Report:
```
✅ Workflow complete! Plan: <plan-path>
Tasks: N/N | Tests: X passed | Iterations: N
```

---

## Rules

- NEVER skip code review agents (Step 3.1)
- ALWAYS resolve SESSION_DIR to a real path before Task calls — never use `<session-id>` placeholder
- Agent prompts must list the specific Files from each plan task (scope limiting)
- Auto-fix ALL must_fix and should_fix findings without asking
- Re-verify after every round of fixes
- The only user interaction is worktree sync approval
