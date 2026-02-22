# /spec-verify - Verification Phase

Phase 3 of the /spec workflow. Runs tests, code review agents, and confirms all plan criteria are met.

**Input:** Path to a COMPLETE plan file
**Output:** Plan status set to VERIFIED (or PENDING with fix tasks added)
**Loop:** If issues found → fix tasks added → `Skill('spec-implement')` → re-verify

---

## Step 3.0: Pre-Verification Check

1. Read the plan file — confirm `Status: COMPLETE`
2. Run full test suite:
   ```bash
   cd tools/cohezion-engine && uv run pytest -q
   ```
   All tests must pass before code review agents run.

---

## Step 3.1: Run Code Review Agents (MANDATORY — NEVER SKIP)

Launch both agents in parallel via Task tool with `run_in_background=true`:

```python
Task(
  subagent_type="general-purpose",
  description="Compliance review",
  prompt="You are a compliance reviewer. Read .claude/agents/spec-reviewer-compliance.md for your instructions, then read the plan at <plan-path> and all changed files. Execute those instructions. Write findings JSON to ~/.cohezion-engine/sessions/<session-id>/compliance.json",
  run_in_background=True
)

Task(
  subagent_type="general-purpose",
  description="Quality review",
  prompt="You are a quality reviewer. Read .claude/agents/spec-reviewer-quality.md for your instructions, then read the plan at <plan-path> and all changed files. Execute those instructions. Write findings JSON to ~/.cohezion-engine/sessions/<session-id>/quality.json",
  run_in_background=True
)
```

Poll output files using Read tool.

---

## Step 3.2: Process Findings (Automatic — No User Confirmation)

For every `must_fix` and `should_fix` finding:

1. Fix immediately without asking permission
2. Re-run the test suite after fixes
3. If fixes require significant new work → add tasks to plan, set `Status: PENDING`, invoke `Skill('spec-implement')`

For `suggestion` findings: implement if quick and low-risk.

**NEVER ask "Should I fix these?" — fix them automatically.**

---

## Step 3.3: Definition of Done Checklist

Validate every task's Definition of Done criteria from the plan. For each criterion:

- [ ] Is it actually implemented?
- [ ] Is it tested?
- [ ] Does the verify command pass?

Run all verify commands listed in the plan's task sections.

---

## Step 3.4: Grep Verification

Confirm no references to the old CLI remain:

```bash
# Check for old binary references (should return no output)
grep -r "~/.pil""ot" .claude/rules/ .claude/commands/ .claude/agents/ .claude/hooks/ 2>/dev/null

# Check for old session env var (should return no output)
grep -r "PIL""OT_SESSION""_ID" .claude/rules/ .claude/commands/ .claude/agents/ 2>/dev/null

# Check for general old-CLI references in commands and agents
grep -r "pil""ot" .claude/commands/ .claude/agents/ 2>/dev/null | grep -v "autopil""ot\|copil""ot"
```

All must return no matches.

---

## Step 3.5: Re-Verification Loop

If any fixes were applied in Step 3.2:

1. Re-run test suite
2. Re-run code review agents (Step 3.1)
3. Repeat until agents return clean (zero must_fix/should_fix findings)

---

## Step 3.6: Worktree Sync (Conditional)

**Only when `Worktree: Yes` in plan header:**

Show user the list of changed files:
```bash
cz worktree diff --json <slug>
```

Ask for sync approval:
```
AskUserQuestion: "Ready to merge worktree changes to base branch?"
Options: Merge and clean up / Keep worktree for now / Discard changes
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

Report completion:
```
✅ Workflow complete! All tasks implemented and verified.
Plan: <plan-path>
Tasks: N/N complete
Tests: X passed
```

---

## Rules

- NEVER skip code review agents (Step 3.1)
- Auto-fix ALL must_fix and should_fix findings without asking
- The only user interaction is worktree sync approval (when Worktree: Yes)
- Re-verify after every round of fixes
- Grep verification is mandatory before VERIFIED status
