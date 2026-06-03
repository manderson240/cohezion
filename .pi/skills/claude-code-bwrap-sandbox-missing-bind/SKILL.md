---
name: claude-code-bwrap-sandbox-missing-bind
description: |
  Diagnose and fix a TOTAL Bash outage in Claude Code on Linux where every command
  (including `claude doctor` and headless `claude -p`) fails with
  `bwrap: Can't create file at <PATH>: No such file or directory`. Root cause is the
  bubblewrap Bash sandbox trying to bind-mount a toolchain path (e.g. /opt/rocm, a CUDA
  dir, an LD_LIBRARY_PATH entry) that an env var pointed at but does not exist on disk.
  Use when: (1) a simple `echo`/`ls`/`grep` fails with a `bwrap` bind error naming a path
  you didn't reference, (2) the failure is identical across all Bash calls, (3)
  `dangerouslyDisableSandbox` does not help, (4) a profile/env file
  (~/.bashrc, ~/.cohezion/*.env) unconditionally exports a *_PATH/PATH to a missing dir.
  Tells you to diagnose with file tools (which bypass the sandbox), guard the export, and
  restart.
author: Claude Code (generic-wondering-octopus session, 2026-06-03)
version: 1.1.0
tags: [claude-code, bwrap, bubblewrap, sandbox, environment, env-var, rocm, ld-library-path, strix-halo, diagnosis, doctor, dev-environment]
---

# Claude Code bwrap sandbox: total Bash outage from a missing bind path

## Problem

On Linux, the Claude Code Bash tool runs commands inside a **bubblewrap (`bwrap`)**
sandbox. The sandbox bind-mounts a set of host paths into the namespace, including
accelerator/toolchain roots it discovers from the environment (e.g. `ROCM_PATH`,
CUDA dirs, `LD_LIBRARY_PATH` entries). If a bind's **source path does not exist**,
`bwrap` exits non-zero **before your command runs** — so *every* Bash command fails
identically, and the error names the missing bind target, not your command.

## Symptoms

- Any Bash call — even `echo hi` — returns:
  ```
  bwrap: Can't create file at <PATH>: No such file or directory
  ```
  (the path varies; it's whatever the sandbox tried and failed to bind)
- The error is **identical across all commands** — strong signal it's the sandbox, not
  your command, your args, or a missing binary.
- `claude doctor` fails the same way (it shells out through the same sandbox).
- A **headless** `claude -p "..."` launched via Bash fails the same way — it is spawned
  *through* the broken sandbox and never starts. Do not reach for headless as a workaround;
  it is circular.
- `dangerouslyDisableSandbox: true` does **not** rescue it (see Gotchas).
- The error message is **misleading**: it names the first failing bind, but the real
  culprit is whichever env var (often `LD_LIBRARY_PATH`, not the most obvious one like
  `ROCM_PATH`) contains the missing path. See "Diagnosis: find the actual env var"
  below — diagnosis by env-var name is a common footgun.

## Root cause

An env var inherited by the Claude Code process at launch points a toolchain path at a
directory that isn't there. Canonical example (AMD Strix Halo box):

```bash
# ~/.bashrc -> source ~/.cohezion/strix_halo.env
export ROCM_PATH=/opt/rocm          # /opt/rocm does not exist
export PATH="/opt/rocm/bin:$PATH"   # phantom PATH entry
```

The sandbox sees the accelerator root and tries `--ro-bind /opt/rocm /opt/rocm`; the
source is missing → `bwrap` aborts. Generalizes to **any** unconditional toolchain export
to a non-existent dir (CUDA, oneAPI, a custom `LD_LIBRARY_PATH`, etc.).

## Diagnostic protocol (Bash is 100% dead — use FILE TOOLS)

The key unlock: **Read / Edit / Write bypass the Bash sandbox** (they go through the
harness, not bwrap). You can run the whole investigation with no working shell.

### Step 1 — Confirm it's the sandbox, not your command
If `echo hi` (or any trivial command) fails with the same `bwrap: Can't create file at
<PATH>` error, it's the sandbox. The `<PATH>` is the missing bind source.

### Step 2 — Find who exports `<PATH>` into the environment
`Read` these in order; stop when you find an unconditional reference to `<PATH>`:
- `~/.claude/settings.json`, project `.claude/settings.json`, `~/.claude/settings.local.json`,
  `/etc/claude-code/managed-settings.json` — look for a `sandbox` block or the path string.
  (Usually NOT here — the bind is auto-derived from env, not configured.)
- The shell profile chain: `~/.bashrc`, `~/.bash_profile`, `~/.profile`, and anything they
  `source` (e.g. `~/.cohezion/*.env`). Look for `export <VAR>=<PATH>` / `PATH=<PATH>/...`.

### Step 3 — Confirm `<PATH>` is genuinely missing
`Read` a file that would exist if the toolchain were installed (e.g.
`/opt/rocm/.info/version`, `/opt/rocm/bin/rocminfo`, or the versioned path
`/opt/rocm-6.x/...`). "File does not exist" across the candidates → the export is stale.
(If it IS installed at a versioned path, the right fix is a symlink, not guarding it away.)

## Diagnosis: find the ACTUAL env var (the named path is often a red herring)

**The `bwrap` error names the first missing bind, but the real culprit is the env var
that points at it, which is often NOT the obvious one.** In a real session
(2026-06-03, harness-bash-unification), the bwrap error said
`bwrap: Can't create file at /opt/rocm: No such file or directory`, suggesting
`ROCM_PATH` was the culprit. It was not. The actual broken var was
`LD_LIBRARY_PATH`:

```bash
LD_LIBRARY_PATH=/usr/lib/mesa-diverted/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu/mesa:/usr/lib/x86_64-linux-gnu/dri:/usr/lib/x86_64-linux-gnu/gallium-pipe
```

The first 3 entries (mesa-diverted, mesa, gallium-pipe) are stale and don't exist on
the live system. The bwrap error named `/opt/rocm` only because that was the first
bind it tried (from `ROCM_PATH`) — but the bwrap run was actually failing on the
missing `LD_LIBRARY_PATH` entry one step later. The error message is a
**first-failing-line, not a true root cause pointer**.

**Diagnostic for the actual culprit** (works without Bash, by reading env via
the Bash tool's pre-failure state OR by running the test with `--print` and a
Read-only task that asks Claude to report what it sees):

```bash
# Run this Bash command (or any Bash command) to see which env vars point at
# non-existent dirs. It works in a fresh bash BEFORE Claude's bwrap kicks in.
for v in LD_LIBRARY_PATH ROCM_PATH HIP_PATH CUDA_PATH PYTHONPATH PATH; do
  val=$(eval echo \$$v)
  if [ -n "$val" ]; then
    IFS=: read -ra parts <<< "$val"
    for p in "${parts[@]}"; do
      [ -n "$p" ] && [ ! -e "$p" ] && echo "MISSING: $v -> $p"
    done
  fi
done
```

The first `MISSING:` line is most likely the real culprit. Fix that one env var
first, retest Bash.

## Fix (durable, self-healing)

### Option A — Guard the export at the source (per-shell)
Guard the export behind an existence check so a missing dir can never poison the env:

```bash
if [ -d /opt/rocm ]; then
    export ROCM_PATH=/opt/rocm
    export PATH="/opt/rocm/bin:$PATH"
fi
```

**General rule:** never `export *_PATH=<dir>` or prepend `<dir>` to `PATH`
unconditionally — guard with `[ -d <dir> ]`. Harmless in a normal shell; fatal inside a
bind-mounting sandbox.

### Option B — Strip bad entries at Claude's parent shell (deployment-script safe)

For headless / programmatic Claude invocations (e.g. `claude --print "..."` from a
Makefile target, a CI script, or a tmux-launched subshell), the source guard may be
in a different shell rc file the script doesn't source. Use a "safe env" wrapper that
filters all PATH-like env vars before Claude spawns:

```bash
# ~/.config/cohezion/safe-env.sh
guard_path_var() {
    local var_name="$1"
    local current="${!var_name:-}"
    [ -z "$current" ] && return 0
    local cleaned=""
    local IFS=':'
    local p
    for p in $current; do
        if [ -n "$p" ] && [ -e "$p" ]; then
            if [ -z "$cleaned" ]; then
                cleaned="$p"
            else
                cleaned="$cleaned:$p"
            fi
        fi
    done
    if [ -z "$cleaned" ]; then
        unset "$var_name"
    else
        export "$var_name=$cleaned"
    fi
}

for v in LD_LIBRARY_PATH PATH PYTHONPATH ROCM_PATH HIP_PATH CUDA_PATH; do
    guard_path_var "$v"
done
```

Then `source ~/.config/cohezion/safe-env.sh && claude --print "bash -c 'echo ok'"`.

**Why this works for deployment scripts:** the script sources the safe env in
*its* subshell before exec'ing Claude. Claude inherits the cleaned env and
bwrap succeeds because every PATH-like entry resolves.

**Verified 2026-06-03** (session harness-bash-unification): the deploy script
`scripts/ci/deploy_harness_agents.sh` launches Claude in a detached tmux
session. Adding `source ~/.config/cohezion/safe-env.sh` at the top of the
launch line brought Claude's Bash tool from 0% to 100% functional. The three
missing entries were `/usr/lib/mesa-diverted/x86_64-linux-gnu`,
`/usr/lib/x86_64-linux-gnu/mesa`, `/usr/lib/x86_64-linux-gnu/gallium-pipe` —
all mesa driver paths from a stale graphics-stack install.

## Clearing the LIVE session (the edit alone is not enough)

The bwrap bind list is built from the environment Claude Code **inherited at launch**, so
the running process keeps the stale bind until one of:
- **Restart Claude Code** (cleanest) — re-sources the guarded profile; the bad var is gone.
- **`sudo mkdir -p <PATH>`** (stopgap, no restart) — makes the bind source exist so `bwrap`
  succeeds immediately. Leaves an empty dir; the guard will then treat it as "present".
- **`source ~/.config/cohezion/safe-env.sh` and re-launch Claude** (no shell restart needed)
  — works because Claude reads its env at process spawn time, not from a cached snapshot.

## Gotchas

- **`dangerouslyDisableSandbox: true` can be a no-op.** With `skipAutoPermissionPrompt:
  true` + `permissions.defaultMode: auto`, a hard sandbox-bypass isn't auto-granted, so the
  command silently runs sandboxed and hits the same broken bind. You see the bwrap error
  again, NOT a permission-denied message. Don't trust the flag to escape a broken sandbox.
- **The error blames the bind target, not the culprit.** The fix lives in the env/profile
  file that set the path, typically two hops upstream.
- **Glob/Bash may both be unavailable** in the degraded session; lean on `Read`/`Edit`/`Write`
  and the schema you already know.

## Related skills

- [[strix-halo-rocm-blocker-triage]] — adjacent but DIFFERENT: that covers ROCm *compute*
  page-faults (GPU hangs, `PERMISSION_FAULTS: 0x3`). This skill is about the *dev-environment
  Bash sandbox*; ROCm is only the incidental path string.
- [[service-port-registry]] / [[strix-halo-fleet-orchestration]] — the local-inference stack
  that actually runs here (lemonade/FLM/Vulkan), explaining why a system ROCm at /opt/rocm
  was absent and the export was stale.

## Reference

- Vault note: `learnings/2026-06-03_claude-code-bwrap-sandbox-missing-bind.md`
- Retro: `learnings/RETRO-2026-06-03-harness-bash-unification.md`
- SurrealDB record: `learnings:bash_unification_2026_06_03` (namespace `cohezion`, db `main`)
- Deploy script that surfaced this: `scripts/ci/deploy_harness_agents.sh`
- Fix applied: `~/.config/cohezion/safe-env.sh`
