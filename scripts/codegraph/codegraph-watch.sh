#!/usr/bin/env bash
# codegraph-watch.sh — SessionStart trigger for the codebase-graph artifact.
#
# READ-ONLY by design. Hook subprocesses cannot reliably persist state writes in
# this environment (see ~/.claude/hooks/retro-watch.sh's note), so this only
# reads and emits a signal to stdout — never writes. It tells a new session that
# a precomputed import+inherits graph exists so it can read the artifact in one
# shot instead of re-parsing ~1400 files.
#
# Signals (consumed per ~/.claude/rules/codegraph.md):
#   [codegraph:ready <path>]              artifact exists and matches current HEAD
#   [codegraph:stale <path>] (gen <a>...) artifact exists but HEAD has moved
#   [codegraph:absent]                    no artifact — run the generator
#
# Always exits 0; never breaks session start.

set -uo pipefail

ARTIFACT="${HOME}/vaults/cohezion-vault/graph/codegraph.json"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd || echo "")"

# Only speak inside the cohezion repo.
[ -n "$REPO_ROOT" ] && [ -f "$REPO_ROOT/src/cohezion/__init__.py" ] || exit 0

if [ ! -f "$ARTIFACT" ]; then
  echo "[codegraph:absent] no codebase-graph artifact — run: python scripts/codegraph/build_graph.py"
  exit 0
fi

# Pure reads: artifact's recorded HEAD vs current HEAD.
gen_sha="$(sed -n 's/.*"head_sha": *"\([0-9a-f]*\)".*/\1/p' "$ARTIFACT" | head -1)"
cur_sha="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "")"

if [ -n "$gen_sha" ] && [ -n "$cur_sha" ] && [ "$gen_sha" != "$cur_sha" ]; then
  echo "[codegraph:stale] ${ARTIFACT} (generated at ${gen_sha:0:9}, HEAD now ${cur_sha:0:9})"
else
  echo "[codegraph:ready] ${ARTIFACT}"
fi
exit 0
