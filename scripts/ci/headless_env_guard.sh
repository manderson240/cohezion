#!/usr/bin/env bash
# headless_env_guard.sh — source this in agent/cron/systemd scopes before shelling
# out to external CLIs (agy, antigravity, editors, browsers).
#
# Prevents the 2026-08-30 crash class: Claude Code's bash-tool env scrubber
# (CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1) strips XDG_RUNTIME_DIR from child scopes.
# Any Qt/GTK app launched there (kde-open via agy's OAuth fallback) hit
# qFatal -> SIGABRT -> 900KB coredump per attempt (9 in one loop).
#
# Also exports BROWSER=echo so OAuth flows degrade to printing the URL instead
# of launching a GUI binary that cannot reach a display.
#
# Usage (in a script or shell profile):
#   source scripts/ci/headless_env_guard.sh
#
# Idempotent: safe to source multiple times. Never overrides an existing
# XDG_RUNTIME_DIR.

# 1. Restore the canonical runtime dir if the env scrubber ate it.
if [ -z "${XDG_RUNTIME_DIR:-}" ]; then
    _guard_dir="/run/user/$(id -u)"
    if [ -d "$_guard_dir" ]; then
        export XDG_RUNTIME_DIR="$_guard_dir"
    fi
    unset _guard_dir
fi

# 2. No display reachable at all? Degrade browser-opening to echo, never GUI-crash.
if [ -z "${XDG_RUNTIME_DIR:-}" ] && [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
    export BROWSER="echo"
    export TERMINAL="echo"
fi

# 3. Headless markers for tools that consult them.
if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
    export BROWSER="${BROWSER:-echo}"
fi

return 0 2>/dev/null || true