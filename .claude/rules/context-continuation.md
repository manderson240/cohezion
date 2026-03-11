# Context Continuation - Endless Mode for All Sessions

**Rule:** When context reaches critical levels, save state and continue seamlessly in a new session.

## Quality Over Speed - CRITICAL

**NEVER rush or compromise quality due to context pressure.**

- You can ALWAYS continue in the next session - work is never lost
- A well-done task split across 2 sessions is better than a rushed task in 1 session
- **Quality is the #1 metric** - clean code, proper tests, thorough implementation
- Do NOT skip tests, compress explanations, or cut corners to "beat" context limits

**The context limit is not your enemy.** It's just a checkpoint. The plan file and continuation files ensure seamless handoff.

### ⛔ But at 90%+, HANDOFF OVERRIDES EVERYTHING

**At 90% context, the handoff IS the quality action.** Failing to hand off means losing ALL work.

- **"Finish current task" means the single tool call in progress** - NOT "fix every remaining error"
- **Do NOT start new fix cycles** at 90%+ (running linters, fixing type errors, running tests)
- **Document remaining errors** in the continuation file for the next session
- The "fix ALL errors" rule is **suspended** at 90%+ - incomplete fixes are expected and acceptable
- The next session will continue exactly where you left off - nothing is lost

## Session Identity

Continuation files are stored under `~/.cohezion-engine/hippocampus/<session-id>/` where `<session-id>` comes from the `COHEZION_SESSION_ID` environment variable (defaults to a PID-based ID if not set).

```bash
echo $COHEZION_SESSION_ID
cz session status --json
```

Then construct the path: `~/.cohezion-engine/hippocampus/<resolved-id>/continuation.md`

## How It Works

This enables "endless mode" for any development session, not just /spec workflows:

1. **Context Monitor hook** warns at 80% and 90% usage (via `context_monitor.py` hook)
2. **You save state** to the continuation file
3. **Session restarts** with a `/clear`, then continuation file is read on next session start
4. **You continue** where you left off

## When Context Warning Appears

When you see the context warning from the context_monitor hook (80% or 90%), take action:

### At 80% - Prepare for Continuation

- Wrap up current task if possible
- Avoid starting new complex work
- Consider saving progress observation

### At 90% - Mandatory Continuation Protocol

**⚠️ CRITICAL: Execute ALL steps below in a SINGLE turn.**

**Step 1: VERIFY Before Writing (CRITICAL)**

Run verification before writing the continuation file:
```bash
uv run pytest -q   # or appropriate test command
```

**Step 2: Check for Active Plan (MANDATORY)**

```bash
ls -1 docs/plans/*.md 2>/dev/null | sort -r | head -5
```

| Situation | Command to Use |
|-----------|----------------|
| Active plan exists (PENDING/COMPLETE) | `cz session send-clear docs/plans/YYYY-MM-DD-name.md` |
| No active plan | `cz session send-clear --general` |

**Step 3: Write Session Summary to File**

Write to the path from `cz session status --json` (key: `session_dir`):

```markdown
# Session Continuation

**Task:** [Brief description]
**Active Plan:** [path/to/plan.md or "None"]

## VERIFIED STATUS:
- Test suite → X passed
- Type checker → X errors

## Completed This Session:
- [x] What was finished

## Next Steps:
1. [IMMEDIATE: First thing to do]
```

**Step 4: Trigger Clear**

```bash
cz session send-clear docs/plans/YYYY-MM-DD-name.md
```

## ⛔ MANDATORY: Clean Up Stale Continuation Files at Session Start

```bash
# Resolve session ID first
cz session status --json  # note the session_dir
rm -f <session_dir>/continuation.md
```

## Resuming After Session Restart

1. Read continuation file: use `cz session status --json` to find the path
2. Delete the continuation file after reading
3. Acknowledge the continuation -- tell user: "Continuing from previous session..."
4. Resume the work from "Next Steps"

## Quick Reference

| Context Level | Action |
|---------------|--------|
| < 80% | Continue normally |
| 80-89% | Wrap up current work, avoid new features |
| ≥ 90% | **MANDATORY:** Save state → Clear session → Continue |

## Commands

```bash
cz context --json           # Check context percentage
cz session status --json    # Show session ID and directory
cz session send-clear <plan.md>    # Trigger continuation with plan
cz session send-clear --general    # Trigger continuation without plan
```
