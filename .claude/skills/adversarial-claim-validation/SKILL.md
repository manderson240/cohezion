---
name: adversarial-claim-validation
description: |
  Systematically verify completion claims with actual commands. Use when:
  (1) user asks to "validate claims", "verify", "check" work, (2) after
  reporting metrics like "X tests pass, Y errors, Z clean", (3) before
  marking work complete. Key insight: run verification commands in parallel
  to check EVERY claim against exact scope (new files vs all files).
author: Claude Code
version: 1.0.0
---

# Adversarial Claim Validation

## Problem

When reporting work completion with metrics ("148 tests pass", "0 type errors",
"linting clean"), claims can be inaccurate due to:
- Testing wrong scope (all files vs new files only)
- Using stale cached results instead of fresh verification
- Mixing pre-existing issues with new code quality
- Over-generalizing partial verification

This erodes trust and wastes user time on false claims.

## Context / Trigger Conditions

**Use this workflow when:**
- User explicitly asks: "validate the claims", "verify", "check", "adversarially validate"
- After reporting completion metrics (test counts, error counts, coverage)
- Before final sign-off on major work (PR creation, plan verification)
- When user questions accuracy: "are you sure?", "did you actually check?"

**Symptoms of need:**
- User asks follow-up questions about numbers you reported
- Discrepancies between your claims and independent verification
- Claims like "all clean" when errors exist in broader scope

## Solution

### Step 1: Identify All Claims

Extract every quantitative claim from your reports:
- Test counts ("147 tests passing")
- Error counts ("0 type errors", "linting clean")
- File counts ("9 production files", "8 test files")
- Status claims ("PR exists", "plan verified")

### Step 2: Determine Exact Scope

For each claim, identify the **exact scope**:
- "0 errors" → in new files only, or entire codebase?
- "tests pass" → which test suite? all tests or subset?
- "files created" → just this PR, or total in directory?

**Default assumption**: if you didn't specify scope, user expects **global** verification.

### Step 3: Run Verification Commands in Parallel

Execute verification commands with explicit scope targeting:

```bash
# NEW files only (scoped verification)
uv run ruff check src/module/new_file.py src/module/other_new.py
uv run basedpyright src/module/new_file.py src/module/other_new.py

# ALL files (global verification)
uv run ruff check src/module/
uv run basedpyright src/module/

# Test counts
uv run pytest tests/module/ -q 2>&1 | grep "passed"

# File existence
ls path/to/file && echo "exists" || echo "missing"

# PR status
gh pr view <number> --json state,mergeable
```

Use parallel Bash invocations when possible to minimize latency.

### Step 4: Report Findings Honestly

Present results in table format:

| Claim | Actual | Verdict |
|-------|--------|---------|
| 147 tests passing | 148 passing | Off by 1 |
| 0 type errors | 10 errors (all pre-existing) | Scope issue |
| Linting clean | 43 errors (16 in new files) | FALSE |
| PR exists | Exists, CONFLICTING | Partial |

**Key principles:**
- Admit errors immediately ("Off by 1", "I was wrong")
- Distinguish pre-existing vs new issues
- Note severity (warnings vs errors)
- Clarify what claims hold with correct scope

### Step 5: Fix or Clarify

Based on findings:
- **Claims accurate with scope clarification** → "0 errors in new files (10 pre-existing in module)"
- **Claims false** → fix the issues, re-verify, update claims
- **Partial truth** → explain nuance (PR exists but has conflicts)

## Verification

After adversarial validation:
- [ ] Every claim verified with fresh command execution
- [ ] Scope explicitly stated for each metric
- [ ] Honest reporting of discrepancies
- [ ] User has accurate picture of work status

## Example

**Original claims:**
- "147 tests passing"
- "0 type errors"
- "Linting clean"
- "PR ready to merge"

**Adversarial validation:**
```bash
# Run in parallel
uv run pytest tests/universe/ -q | tail -1
# → "148 passed" (claimed 147, off by 1)

uv run basedpyright src/cohezion/universe/*.py | grep -c "error:"
# → "0" (new files clean)

uv run basedpyright src/cohezion/universe/ | grep -c "error:"
# → "10" (pre-existing errors in old files)

uv run ruff check src/cohezion/universe/*.py
# → "16 errors" (some in new files)

gh pr view 16 --json mergeable
# → "CONFLICTING" (not ready)
```

**Revised claims:**
- Tests: 148 passing (claimed 147, off by 1)
- Type errors: 0 in new files, 10 pre-existing in module
- Linting: 16 errors in new files (need fixes)
- PR: exists but has merge conflicts

## References

- Pattern emerged from Session 2026-02-19: user requested adversarial validation
- Verification-before-completion rule: `.claude/rules/verification-before-completion.md`
