# Fix SessionStart Hook Error & Improve Entire.io Integration

## Context

Every session start shows "SessionStart:startup hook error" because `entire hooks claude-code session-start` exits 1 with "no session_id in SessionStart event". GitHub issue [entireio/cli#237](https://github.com/entireio/cli/issues/237) describes the same bug — resolved by reinstalling hooks via `entire enable --force`.

Additionally, our Entire integration is incomplete: we're missing 3 of the 7 hooks that Entire v0.5.3 installs, and aren't using several features (auto-summarization, subagent tracking, `entire resume`).

**Root cause**: Hooks were manually added to `.claude/settings.json` with `matcher: "all"` instead of being installed by `entire enable` (which uses `matcher: ""`). This may affect how Claude Code pipes stdin JSON to the hook.

## Part 1: Fix the Hook Error

### Step 1: Diagnose (capture actual stdin)

Add a `tee` debug wrapper to confirm what Claude Code sends:
```bash
# Temporarily change the hook command in .claude/settings.json to:
"command": "bash -c 'cat | tee /tmp/entire-session-start-debug.json | entire hooks claude-code session-start'"
```

After one session start, read `/tmp/entire-session-start-debug.json` to confirm the JSON payload.

### Step 2: Reinstall hooks via `entire enable`

Run `entire enable --agent claude-code --force --project` to let Entire install all hooks correctly. This:
- Removes existing Entire hooks (only `entire`-prefixed commands — preserves our custom hooks)
- Installs all 7 hooks with correct `matcher` values
- Adds `Read(./.entire/metadata/**)` to `permissions.deny`

**Files modified**: `.claude/settings.json` (project)

**Risk**: `entire enable` re-serializes the full JSON, which may reorder fields. We'll `git diff` after to review.

### Step 3: Verify

1. Start a new Claude Code session → no "startup hook error"
2. Check logs: `tail -5 .entire/logs/entire.log | grep session-start`
3. Confirm all 7 hooks present: `grep -c "entire hooks claude-code" .claude/settings.json` → should be 7

## Part 2: Better Leverage Entire

### Step 4: Enable auto-summarization

Update `.entire/settings.json` to enable AI summaries at commit time:
```json
{
  "enabled": true,
  "strategy_options": {
    "summarize": {
      "enabled": true
    }
  }
}
```

This generates concise summaries of what changed in each checkpoint, making `entire explain` more useful.

### Step 5: Update continuation workflow in CLAUDE.md

Add `entire resume` as a complementary tool alongside our `cz session send-clear` workflow. The `entire resume` command:
- Switches to the branch where the session was active
- Restores metadata and session state
- Shows continuation commands from the last checkpoint

Update the "Entire Context Recovery" section in CLAUDE.md to include:
```markdown
### Entire Context Recovery
```bash
entire explain --short 2>/dev/null | head -10      # Recent checkpoints
entire resume <branch>                              # Resume from checkpoint
entire doctor                                       # Fix stuck sessions
entire sessions stop                                # Clean stale sessions
```
```

### Step 6: Add `entire doctor` to troubleshooting

Add to the session-concierge or a new hook: if `entire status` shows stuck sessions, warn.

## Files to Modify

| File | Action | Why |
|------|--------|-----|
| `.claude/settings.json` | **Overwrite by `entire enable --force`** | Fix hooks, add missing 3 |
| `.entire/settings.json` | **Edit** | Enable auto-summarization |
| `CLAUDE.md` | **Edit** | Document `entire resume/doctor/sessions` |

## Verification

1. `entire enable --agent claude-code --force --project` → "Installed 7 hooks"
2. Start new session → no "SessionStart:startup hook error"
3. Make a commit → check `entire explain --short` shows summary
4. `grep "entire hooks claude-code" .claude/settings.json | wc -l` → 7
5. `.entire/logs/entire.log` shows `session-start` with valid session_id

## References

- [entireio/cli#237](https://github.com/entireio/cli/issues/237) — Same error, fixed by reinstalling
- [entireio/cli source: hooks.go](https://github.com/entireio/cli/blob/main/cmd/entire/cli/agent/claudecode/hooks.go) — Hook installation logic
- [entireio/cli README](https://github.com/entireio/cli) — Full feature documentation
