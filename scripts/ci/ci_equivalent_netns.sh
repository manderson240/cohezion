#!/usr/bin/env bash
# CI-equivalent test run: the three ci.yml tiers inside a network namespace with loopback up
# and NOTHING listening, which is what ubuntu-latest looks like to this suite (CI provisions no
# SurrealDB, no Lemonade, no Ollama). Every local-service probe gets an immediate connection
# refusal instead of this machine's live fleet, so "is the repo green" is answered the way CI
# will answer it, not the way a developer box with 5 resident models answers it.
#
# Why this exists (2026-10-22): 216 integration failures hid behind continue-on-error; when
# they were finally run locally, 43 failed WITH live services and only 3 without them. Chasing
# the 40 live-only failures would have been wasted work. Run this before any green claim.
#
# Requirements: unprivileged user namespaces (works on this host; the Claude agent sandbox
# cannot unshare, so run it from a normal shell or the Terminal panel). Must run from the
# checkout under test with PYTHONPATH pinned to ITS src: the venv's editable install points at
# the primary checkout, so an unpinned run silently tests the wrong tree.
#
# Usage:
#   scripts/ci/ci_equivalent_netns.sh                 # all three tiers, log to .cache/ci_equiv.log
#   scripts/ci/ci_equivalent_netns.sh integration      # one tier: unit | inference | integration
#   CI_EQUIV_JOBS=6 scripts/ci/ci_equivalent_netns.sh  # xdist workers for unit/integration (default 6)
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# Interpreter: must be able to import pytest AND xdist. A clone or worktree often carries a stub
# .venv (created by a stray `uv run`) that lacks the test extras; preferring it ran pytest without
# xdist and reported "unrecognized arguments: -n". Resolution: CI_EQUIV_PYTHON, else walk upward
# from this tree and take the first .venv that proves it can import both (worktrees and shared
# clones live under the primary checkout, whose .venv is the real one).
_usable() { [ -x "$1" ] && "$1" -c "import pytest, xdist" >/dev/null 2>&1; }
PY=""
if [ -n "${CI_EQUIV_PYTHON:-}" ]; then
  # An explicit override is honoured or refused, never silently replaced: the variable's name
  # promises to choose the interpreter, so falling back behind the caller's back would be a
  # false contract (the first draft did exactly that).
  _usable "$CI_EQUIV_PYTHON" || { echo "ci_equivalent_netns: CI_EQUIV_PYTHON=$CI_EQUIV_PYTHON cannot import pytest and xdist" >&2; exit 3; }
  PY="$CI_EQUIV_PYTHON"
fi
d="$ROOT"
while [ -z "$PY" ] && [ "$d" != "/" ]; do
  _usable "$d/.venv/bin/python" && PY="$d/.venv/bin/python"
  d="$(dirname "$d")"
done
if [ -z "$PY" ]; then
  echo "ci_equivalent_netns: no .venv with pytest+xdist found walking up from $ROOT; set CI_EQUIV_PYTHON" >&2
  exit 3
fi
JOBS="${CI_EQUIV_JOBS:-6}"
LOG="${CI_EQUIV_LOG:-$ROOT/.cache/ci_equiv.log}"
TIER="${1:-all}"
mkdir -p "$(dirname "$LOG")"

if ! unshare -rn true 2>/dev/null; then
  echo "ci_equivalent_netns: cannot create a user+network namespace here (agent sandbox?)." >&2
  echo "Run from a normal shell: bash scripts/ci/ci_equivalent_netns.sh" >&2
  exit 3
fi

export PYTHONPATH="$ROOT/src"
cd "$ROOT" || exit 1
: > "$LOG"
echo "ci_equivalent_netns: root=$ROOT python=$PY jobs=$JOBS tier=$TIER log=$LOG"

# Each tier runs in its own namespace; the inner command is built explicitly (no function
# re-serialisation) so pytest sees exactly the arguments shown here.
tier() {
  local name="$1"; shift
  echo "### TIER $name ###" | tee -a "$LOG"
  # pipefail inside the namespace so the tier's exit code is pytest's, not tail's; recorded so a
  # usage error (exit 4) or collection abort (exit 2/5) can never read as green.
  unshare -rn bash -c "set -o pipefail; ip link set lo up; '$PY' -m pytest $* -q -p no:warnings -p no:cacheprovider --tb=line -rfE 2>&1 | tail -60" | tee -a "$LOG"
  local rc=${PIPESTATUS[0]}
  echo "### TIER $name exit=$rc ###" | tee -a "$LOG"
  [ "$rc" -eq 0 ] || TIER_FAILURES=$((TIER_FAILURES + 1))
}
TIER_FAILURES=0

unshare -rn bash -c "ip link set lo up; '$PY' -c 'import cohezion; print(\"cohezion from\", cohezion.__file__)'" | tee -a "$LOG"

case "$TIER" in unit|all)        tier unit tests/unit/ -n "$JOBS" ;; esac
case "$TIER" in inference|all)   tier inference tests/inference/ ;; esac
case "$TIER" in integration|all) tier integration tests/ --ignore=tests/unit/ --ignore=tests/inference/ -n "$JOBS" ;; esac

echo "### CI_EQUIV_DONE ###" | tee -a "$LOG"
if [ "$TIER_FAILURES" -ne 0 ] || grep -qE '^(FAILED|ERROR) ' "$LOG"; then
  echo "ci_equivalent_netns: NOT GREEN — $TIER_FAILURES tier(s) exited non-zero (see $LOG):"
  grep -E '^(FAILED|ERROR) |exit=[1-9]' "$LOG" | head -40; exit 1
fi
echo "ci_equivalent_netns: all requested tiers green in a no-services namespace"
