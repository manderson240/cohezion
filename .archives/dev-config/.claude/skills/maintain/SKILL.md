---
name: maintain
description: Autonomous vault and codebase maintenance cycle. Scans for issues
  (orphan notes, broken links, missing __init__.py, lint errors, stubs), prioritizes
  by impact, fixes the top N issues, and verifies repairs. Use for periodic hygiene
  or when the codebase feels "crusty".
arguments:
  - name: count
    description: Maximum number of issues to fix in this cycle (default 10)
    required: false
---

# Autonomous Maintenance Cycle

You are running a maintenance cycle. Fix up to `$ARGUMENTS` issues (default: 10). Be surgical — every fix must leave the codebase strictly better.

## Step 0: Dependency Health Check

Before scanning code, verify infrastructure is reachable:

```bash
# Check SurrealDB
curl -sf http://localhost:8000/health && echo "SurrealDB: OK" || echo "SurrealDB: DOWN"

# Check Ollama
curl -sf http://localhost:11434/api/tags && echo "Ollama: OK" || echo "Ollama: DOWN"
```

If a dependency is down:
- Diagnose: Is the service installed? Is the port in use by something else? Check systemd/process status.
- Report the diagnosis but do NOT attempt to fix infrastructure (that requires user decisions).
- Continue with maintenance tasks that don't require the downed service.

## Step 1: Audit — Scan for Issues

Run each scan and collect issues into a prioritized list:

### 1a. Python Package Health
```bash
# Missing __init__.py in src/ directories
find src/cohezion -type d ! -exec test -e '{}/__init__.py' \; -print 2>/dev/null

# Unused imports and lint errors
uv run ruff check src/cohezion/ --select F401,E,W --statistics 2>/dev/null | head -20
```

### 1b. Test Health
```bash
# Current test state
uv run pytest tests/ -q --tb=no 2>&1 | tail -5

# Find test files with no test functions
grep -rL "def test_" tests/test_*.py tests/**/test_*.py 2>/dev/null
```

### 1c. Vault Health (if SurrealDB is up)
Use vault tools to check:
- Orphan notes (no backlinks, no forward links)
- Broken internal links (references to non-existent notes)
- Stub notes (created but never filled in — less than 50 characters)

### 1d. Codebase Hygiene
```bash
# Files over 500 lines (hard limit per coding standards)
find src/cohezion -name "*.py" -exec awk 'END{if(NR>500)print FILENAME": "NR" lines"}' {} \;

# Dead code candidates: functions defined but never referenced elsewhere
# (lightweight check — grep for def names not found in other files)
```

## Step 2: Prioritize by Impact

Score each issue:

| Priority | Category | Examples |
|----------|----------|---------|
| P0 - Critical | Breaks tests or imports | Missing `__init__.py`, syntax errors, failing tests |
| P1 - High | Affects code quality | Lint errors (E, W), files over 500 lines, unused imports |
| P2 - Medium | Knowledge rot | Orphan vault notes, broken links, empty stubs |
| P3 - Low | Cosmetic | Minor formatting, non-blocking warnings |

Sort by priority. Take the top N (from `$ARGUMENTS`, default 10).

## Step 3: Fix Issues

For each issue, in priority order:

1. **Read** the affected file/note
2. **Fix** the specific issue (minimal change — do not refactor surrounding code)
3. **Verify** the fix:
   - For Python changes: `uv run pytest tests/ -q --tb=short` (must not regress)
   - For vault changes: Confirm the link/note now resolves
   - For lint fixes: `uv run ruff check <file> --select F401,E,W`
4. **Record** what you fixed (file, issue, fix applied)

### Self-Correction Rule

After each fix, run tests. If a fix **introduces** a new failure:
- Immediately revert the change
- Record it as "attempted but reverted — caused regression"
- Move to the next issue

Do NOT spend more than 3 minutes debugging a single maintenance fix. If it's not straightforward, skip it and note it for manual review.

## Step 4: Verify Overall Health

After all fixes:

```bash
# Full test suite
uv run pytest tests/ -q --tb=no

# Lint check
uv run ruff check src/cohezion/ --statistics 2>/dev/null | tail -5
```

Compare with Step 1 baseline:
- Test count: before vs. after (must not decrease)
- Lint issue count: before vs. after (must decrease or stay same)
- Failing tests: before vs. after (must not increase)

## Step 5: Report

```
## Maintenance Report

**Scanned**: <timestamp>
**Issues found**: <total>
**Issues fixed**: <fixed count> / <attempted count>
**Issues skipped**: <skipped count> (with reasons)
**Reverted**: <reverted count> (caused regressions)

### Fixes Applied
| # | File | Issue | Fix | Verified |
|---|------|-------|-----|----------|
| 1 | src/cohezion/foo/bar.py | Missing __init__.py | Created file | Tests pass |
| 2 | vault: orphan-note.md | No backlinks | Added link from index | Link resolves |

### Health Delta
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Tests passing | X | Y | +Z |
| Lint errors | A | B | -C |
| Vault orphans | D | E | -F |

### Skipped (needs manual review)
- <file>: <issue> — <reason skipped>
```

## Hard Rules

| Rule | Rationale |
|------|-----------|
| Never refactor during maintenance | Maintenance fixes specific issues, not "improves" code |
| Revert any fix that causes regression | Leave codebase strictly better, never worse |
| Do not add features during maintenance | Maintenance is hygiene, not development |
| Do not modify test assertions to make them pass | Fix the code, not the tests |
| Report honestly — include reverts and skips | Transparency over vanity metrics |
| Do not fix infrastructure (SurrealDB, Ollama) without user | Infrastructure changes need human judgment |

## Anti-Patterns

- "While I'm here, let me also refactor this module..." — NO. Fix the listed issue only.
- Marking an issue as fixed without running verification — NO. Evidence required.
- Silently skipping issues to report a higher success rate — NO. Report skips.
- Spending 20 minutes on one lint error — NO. 3-minute cap per issue, then skip.
- Deleting files to "fix" orphan warnings — NO. Investigate first, delete only true orphans.
