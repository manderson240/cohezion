#!/usr/bin/env bash
# SessionStart hook — emit a [branch-hygiene] signal when the repo is adrift from a
# clean landing posture (sitting on main, or a feature branch far ahead of main).
#
# Deterministic, $0, no inference. Mirrors ~/.claude/hooks/version-watch.sh: it does
# NOT act — it emits a one-line signal that ~/.claude/rules/branch-landing-protocol.md
# reacts to. Fail-OPEN: any internal error exits 0 silently; it only ever speaks when
# there is something worth acting on.
set -uo pipefail

cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0   # not a git repo → silent

branch=$(git branch --show-current 2>/dev/null || true)
[ -n "$branch" ] || exit 0                                       # detached HEAD → silent

base=origin/main
git rev-parse --verify -q "$base" >/dev/null 2>&1 || base=origin/master
git rev-parse --verify -q "$base" >/dev/null 2>&1 || exit 0      # no upstream main → silent

ahead=$(git rev-list --count "${base}..HEAD" 2>/dev/null || echo 0)
case "$branch" in main|master) on_main=yes ;; *) on_main=no ;; esac

# Speak only on a real signal: on main, or a feature branch >=5 commits ahead
# (the threshold that flagged fix/repo-health-enforcement's cz+repo-health mixing).
if [ "$on_main" = yes ] || [ "${ahead:-0}" -ge 5 ]; then
  echo "[branch-hygiene] on ${branch}, ${ahead} ahead of ${base}, on-main=${on_main}"
fi
exit 0
