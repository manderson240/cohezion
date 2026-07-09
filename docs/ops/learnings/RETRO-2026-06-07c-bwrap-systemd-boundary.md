---
date: 2026-06-07
kind: retro
thread: [ops, sandbox]
prompted_by: retro-watch ([retro:due], 10 tasks)
status: captured
supersedes_detail_in: RETRO-2026-06-07.md (#4)
---

# Retro — the precise reason the agent can't reach the user systemd/D-Bus session

Prior retros noted "sandbox bypass ≠ user systemd bus." This session fully diagnosed the
mechanism (the user asked "why can't you reach system bus"), so pin the exact cause — it ends
the recurring temptation to retry `dangerouslyDisableSandbox` for `systemctl --user` work.

## The mechanism (verified)

The agent shell runs as PID 2 inside a `bwrap` sandbox (PID 1). Its launch line contains:

    bwrap … --bind /run /run … --tmpfs /run/user … --tmpfs /run/dbus …

So even though:
- I AM uid 1000 (mike-anderson),
- `XDG_RUNTIME_DIR=/run/user/1000` and `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`
  are both correctly set,

…the `--tmpfs /run/user` mounts a **fresh empty in-memory filesystem over `/run/user`**, shadowing
the host's real `/run/user/1000/bus` D-Bus socket. `ls /run/user/1000/` → "No such file or
directory" inside my namespace, while the host has it (your gateway runs fine). Hence
`systemctl --user …` → "Failed to connect to user scope bus via local transport: No such file
or directory."

## Why `dangerouslyDisableSandbox` does NOT help

That flag relaxes the **filesystem/network access policy** (what I may read/write/reach). It does
NOT give me a new mount namespace — `ps` confirms the same `bwrap` (with `--tmpfs /run/user`) is
still my PID 1 even on a bypassed command. The empty overlay is baked into the namespace at
launch; bypass can't reconstruct a socket that isn't mounted. It is an **architecture boundary**,
not a permissions gate.

## Operational consequence (the rule)

Anything that needs the user's login D-Bus session must run from the USER's shell, not the agent:
- restarting the `--user` Hermes gateway (`systemctl --user restart hermes-gateway`),
- editing its config behind a stop (the write-back race fix),
- clearing `~/.claude/.retro-pending` (that path is `--ro-bind` in my namespace too).

The delivery path for these is the `! <command>` prefix the user types, which runs in their
session (outside bwrap). The agent's job is to PREPARE the exact command/script (e.g.
`scripts/hermes/fix_bot_empty_response.sh`) and hand it over — not to keep retrying the bypass.

Everything that does NOT need that socket (git push/commit, file edits, the loops, local HTTP to
:13305) the agent runs directly and has been doing throughout.

## This stretch's other note (already actioned, not re-extracted)
- The wiring sweep surfaced a real latent bug: `executor_integration.validate_sandbox()` imports a
  nonexistent `validate_sandbox_task`, swallowed by `except ImportError: return True` → sandbox
  validation silently disabled. Recorded under WIRING_SWEEP_LEDGER "Needs human decision"
  (behavior-changing fix, not auto-applied). Anti-pattern worth remembering: `except ImportError:
  return <permissive-default>` around a same-repo import hides a broken edge AND fails OPEN.
