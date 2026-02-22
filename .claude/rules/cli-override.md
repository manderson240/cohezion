## CLI Reference (cohezion-engine)

> **This file replaces the global CLI reference rule for the cohezion-vault project.**
> This project uses `cz` (cohezion-engine) instead of the previous CLI.
> See `cz-cli.md` for the full command reference.

All session, context, worktree, and plan management is done via `cz` commands.
The session ID environment variable is `COHEZION_SESSION_ID`.
Session files live at `~/.cohezion-engine/sessions/<session-id>/`.
