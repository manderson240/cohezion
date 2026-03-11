# Session Registry

Tracks active and recent Claude Code sessions across local and remote instances.
Update this note at session start/end using `vault_edit` or `vault_write`.

**Protocol:**
- On session start: add a row with status `active`
- On session end/handoff: update status to `complete` or `handed-off`
- Keep only the last 20 entries (prune older ones when adding new)

---

## Active Sessions

| Session ID | Goal | Worktree Branch | Model | Started | Status |
|------------|------|-----------------|-------|---------|--------|
| _(none currently active)_ | | | | | |

---

## How to Register Your Session

At the **start** of any session, prepend a row to the Active Sessions table:

```
| <session-id> | <1-line goal> | <branch or main> | sonnet-4-6 | <date> | active |
```

Get your session ID: `cz session status --json`

At the **end** of a session, update your row's status to one of:
- `complete` — work finished and committed
- `handed-off` — continuation file written, next session picks up
- `paused` — work saved to vault, resuming later

---

## Coordination Rules

1. **One worktree per session** — never two sessions on the same branch
2. **Teleport for handoffs** — use `teleport_create_task` to pass work between sessions
3. **Vault is shared state** — log decisions/experiments so all sessions benefit
4. **Check before starting** — if another session is working on the same area, coordinate via teleport

---

## Recent Sessions (last 20)

| Session ID | Goal | Branch | Completed | Outcome |
|------------|------|--------|-----------|---------|
| setup-remote-leverage | GitHub templates + scout workflow + session registry | main | 2026-03-05 | complete |

---

## Quick Reference

```bash
# Get your session ID
cz session status --json

# Queue work for another session
mcp-cli cohezion-vault/teleport_create_task '{"title": "...", "description": "...", "priority": "high"}'

# Check pending tasks
mcp-cli cohezion-vault/teleport_list_tasks '{"status": "pending"}'

# Start overnight compound run
nohup uv run python scripts/drivers/overnight_driver.py > /tmp/cohezion-overnight.log 2>&1 &

# Trigger remote Claude via GitHub (from phone)
# Open github.com → Issues → New Issue → "Claude Command" template
```
