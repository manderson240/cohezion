## Cohezion Engine CLI (`cz`) Reference

The `cz` binary is the cohezion-engine workflow CLI. Install via:
```bash
cd tools/cohezion-engine && uv pip install -e .
```

**These are all available commands -- do NOT call commands that aren't listed here.**

### Session & Context

| Command | Purpose | JSON Output |
|---------|---------|-------------|
| `cz context --json` | Get context usage percentage | `{"status": "OK", "percentage": 47.0}` |
| `cz session status --json` | Show current session ID and directory | `{"session_id": "...", "session_dir": "..."}` |
| `cz session send-clear <plan.md>` | Trigger continuation with plan | Writes trigger, attempts WebSocket restart |
| `cz session send-clear --general` | Trigger continuation without plan | Same, without plan context |

**Context status values:**
- `OK` — below 80%
- `WARNING` — 80–89%
- `CLEAR_NEEDED` — 90%+ (hand off immediately)

**Session ID:** Uses `COHEZION_SESSION_ID` env var, falls back to `pid-<PID>`.
**Session directory:** `~/.cohezion-engine/sessions/<session-id>/`
**Continuation file:** `~/.cohezion-engine/sessions/<session-id>/continuation.md`

### Worktree Management

| Command | Purpose | JSON Output |
|---------|---------|-------------|
| `cz worktree detect --json <slug>` | Check if worktree exists | `{"found": true, "path": "...", "branch": "...", "base_branch": "..."}` |
| `cz worktree create --json <slug>` | Create worktree on new branch | `{"success": true, "path": "...", "branch": "spec/<slug>", "base_branch": "main"}` |
| `cz worktree diff --json <slug>` | List changed files vs base branch | `{"success": true, "files_changed": [...], "count": N}` |
| `cz worktree sync --json <slug>` | Squash merge worktree to base branch | `{"success": true, "files_changed": N, "commit_hash": "..."}` |
| `cz worktree cleanup --json <slug>` | Remove worktree and branch | `{"success": true, "removed_path": "...", "deleted_branch": "..."}` |
| `cz worktree status --json` | Show active worktree info | `{"active": false}` or `{"active": true, "branch": "...", "slug": "...", "path": "..."}` |

**Slug:** Plan filename without date prefix and `.md` (e.g., `2026-02-11-add-auth.md` → `add-auth`).

**Error handling:** `create` returns `{"success": false, "error": "dirty", "detail": "..."}` when the working tree has uncommitted changes.

### Plan Management

| Command | Purpose |
|---------|---------|
| `cz plan register <path> <status>` | Associate plan with current session |
| `cz plan status --json` | Show registered plan and parsed frontmatter |

### Other

| Command | Purpose |
|---------|---------|
| `cz status --json` | Show version and config dir |
| `cz --version` | Show version |
| `cz --help` | Show all commands |

### Commands That Do NOT Exist

- ~~`cz activate`~~ — No license management for internal tool
- ~~`cz pipe`~~ — Not implemented
- ~~`cz greet`~~ — Not implemented
- ~~`cz statusline`~~ — Deferred (see Open Questions in plan)
