#!/usr/bin/env bash
# Source this before running CI gates by hand:  source scripts/ci/gate_env.sh
#
# WHY THIS EXISTS
# Agent worktrees are mounted read-only. Every gate tool writes a cache into the tree by default,
# so each one fails with a message that names the TOOL, not the filesystem -- and reads exactly
# like "your change broke lint/types". Measured in a single session (2026-09-22): ruff
# ("ruff failed / Failed to create temporary file"), mypy (empty output -> the ratchet refuses to
# gate), uv ("failed to create directory .venv"), the pre-commit hook (same uv failure), and
# mutmut (no results to parse). Five different-looking failures, one cause.
#
# Phase 0 applies to gates as much as to research: a negative from an instrument that could not
# run is UNKNOWN, not FAIL. This script makes the instruments able to run, and REFUSES to proceed
# when the most dangerous misconfiguration is present.
#
# THE SILENT ONE
# Borrowing another checkout's venv is not merely convenient -- its editable install resolves
# `cohezion` to THAT checkout's src/, so pytest greens against code you did not change. That
# failure has no error message at all, which is why the import assertion below is fatal rather
# than a warning.

_gate_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Caches go somewhere writable. TMPDIR is set per-session by the harness; fall back to mktemp.
_gate_cache="${TMPDIR:-$(mktemp -d)}/cohezion-gate-cache"
mkdir -p "$_gate_cache/ruff" "$_gate_cache/mypy"
export RUFF_CACHE_DIR="$_gate_cache/ruff"
export MYPY_CACHE_DIR="$_gate_cache/mypy"
# pytest's cache is only a warning, but it is noise on every single run.
export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} -p no:cacheprovider"

# uv creates .venv in the project root, which fails here. Point it at an existing environment
# ONLY when this tree has none of its own -- a local .venv always wins.
if [ ! -x "$_gate_root/.venv/bin/python3" ]; then
  export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-/home/mike-anderson/dev/cohezion/.venv}"
  # ...and that borrowed venv is exactly the silent-wrong-tree hazard, so force our src/ ahead of
  # its editable install.
  export PYTHONPATH="$_gate_root/src${PYTHONPATH:+:$PYTHONPATH}"
fi

# Fatal assertion: prove the tree under test is THIS tree before any gate is believed.
_gate_resolved="$(uv run --no-sync python -c 'import cohezion; print(cohezion.__file__)' 2>/dev/null | tail -1)"
case "$_gate_resolved" in
  "$_gate_root"/*)
    echo "gate_env: OK — cohezion resolves to $_gate_root" ;;
  "")
    echo "gate_env: FATAL — could not import cohezion at all; gates would report UNKNOWN as FAIL" >&2
    return 1 2>/dev/null || exit 1 ;;
  *)
    echo "gate_env: FATAL — cohezion resolves to $_gate_resolved" >&2
    echo "gate_env:         but gates would be attributed to $_gate_root" >&2
    echo "gate_env:         you would be testing a tree you did not change. Refusing." >&2
    return 1 2>/dev/null || exit 1 ;;
esac

# Not fixable by redirection: mutmut needs a writable mutants/ cache in the tree, so the mutation
# ratchet cannot run from a read-only worktree at all. It fails CLOSED (refuses to parse empty
# output) rather than reporting a false pass -- treat that as UNKNOWN and run it from a writable
# clone, never as a gate failure to be "fixed".
echo "gate_env: note — mutation ratchet needs a writable tree; UNKNOWN here, not FAIL"
