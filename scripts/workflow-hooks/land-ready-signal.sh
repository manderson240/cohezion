#!/usr/bin/env bash
# Stop hook — emit a quiet, once-per-branch [land:ready] nudge when a feature branch
# looks landable: not main/master, ahead of origin/main, and a CLEAN working tree.
#
# This is a NUDGE, not a trigger. It is deliberately cheap: it does NOT run gates or
# reviews (Stop fires constantly). The expensive pipeline (gates + adversarial review +
# semver + fast-forward) runs only when the user confirms — see branch-landing-protocol.md.
# Rate-limited to once per branch (a seen-set) so it never nags across a work session.
#
# Deterministic, $0, no inference. Fail-OPEN silent: any error exits 0 with no output.
set -uo pipefail

cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

branch=$(git branch --show-current 2>/dev/null || true)
[ -n "$branch" ] || exit 0                                   # detached HEAD → silent
case "$branch" in main|master) exit 0 ;; esac               # only feature branches land

base=origin/main
git rev-parse --verify -q "$base" >/dev/null 2>&1 || base=origin/master
git rev-parse --verify -q "$base" >/dev/null 2>&1 || exit 0

ahead=$(git rev-list --count "${base}..HEAD" 2>/dev/null || echo 0)
[ "${ahead:-0}" -ge 1 ] || exit 0                            # nothing ahead → nothing to land
[ -z "$(git status --porcelain 2>/dev/null)" ] || exit 0    # dirty tree → not landable yet

# Rate-limit: emit once per branch (seen-set), so it nudges when a branch first becomes
# landable and stays quiet as you keep committing to it.
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/cohezion"
mkdir -p "$state_dir" 2>/dev/null || state_dir="${TMPDIR:-/tmp}"
seen="$state_dir/land-ready.seen"
repo=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || echo repo)")
key="${repo}:${branch}"
if [ -f "$seen" ] && grep -qxF "$key" "$seen" 2>/dev/null; then
  exit 0                                                     # already nudged for this branch
fi
printf '%s\n' "$key" >> "$seen" 2>/dev/null || true

echo "[land:ready] ${branch} (${ahead} ahead of ${base}, clean tree) — say 'land it' to run the gated pipeline"

# Feed the ambient datamesh: publish a land_ready event so the ALREADY-RUNNING
# cohezion-event-consumer routes it to the land runner (gates + review + semver → kanban
# for human approval). Best-effort — the session nudge above already fired; the daemon
# path is the agentic CI/CD runner. Rate-limited to once per branch by the seen-set above.
repo_top=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
ts=$(date +%s)   # data_product_event.timestamp is TYPE float (epoch) — NOT a datetime
payload=$(printf '{\\"repo\\":\\"%s\\",\\"branch\\":\\"%s\\",\\"base\\":\\"%s\\",\\"ahead\\":%s}' \
  "$repo_top" "$branch" "$base" "${ahead:-0}")
curl -s --max-time 5 http://127.0.0.1:8001/sql \
  -H "surreal-ns: cohezion" -H "surreal-db: main" -H "Content-Type: text/plain" \
  -H "Authorization: Basic $(printf 'root:root' | base64 | tr -d '\n')" \
  --data "CREATE data_product_event SET event_type='land_ready', source='land-ready-signal', timestamp=${ts}.0, payload=\"${payload}\", priority=5;" \
  >/dev/null 2>&1 || true
exit 0
