# Ralph Loop Safety Rules

## MANDATORY: Exit Conditions

**NEVER start a Ralph loop without an exit condition.** Every `/ralph-loop` invocation MUST have:

```
--completion-promise "specific testable condition"
```

OR:

```
--max-iterations N  (where N = 2x expected productive cycles)
```

## Why

Session 88B: 721 iterations, 8 productive, 713 wasted. The stop hook cannot distinguish "work complete" from "still working." Without an exit condition, the loop runs until context exhaustion.

## Good Completion Promises

- `"All plan phases marked [x] and committed"`
- `"Tests pass and benchmark shows improvement"`
- `"Continuation file written and send-clear triggered"`

## Bad/Missing Promises

- `null` — runs forever
- `"Done"` — too vague, never testable
- No promise at all — same as null

## Research-Before-Build Rule

When dispatching research agents alongside implementation:
1. Wait for research results BEFORE building implementation
2. Or: build minimal PoC, gate full implementation on research findings
3. Never build 5 variants based on assumptions while research is still running

## Email/Notification Prerequisite

Before creating notification scripts, verify the delivery mechanism:
```bash
# Check SMTP is configured
test -n "$COHEZION_SMTP_HOST" || echo "WARNING: SMTP not configured — emails will not send"
```
