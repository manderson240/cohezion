#!/usr/bin/env bash
# Nightly verification bundle (verification-depth.md) — the DETERMINISTIC half of the scheduled
# adversarial pass. Runs the dormancy gate + un-mocked integration smoke (+ the fast unit suite in
# full mode), exits non-zero on ANY failure. The LLM 4-lens adversarial-review half is driven by the
# cron trigger that calls this script and then reviews the day's commits on the local fleet ($0).
#
#   scripts/ci/nightly_verification.sh           # full (adds the unit suite)
#   scripts/ci/nightly_verification.sh --quick   # dormancy + integration smoke only (fast)
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 2

QUICK=0
[ "${1:-}" = "--quick" ] && QUICK=1
fail=0

step() {
  local name="$1"; shift
  echo "== ${name} =="
  if "$@"; then echo "  -> PASS"; else echo "  -> FAIL"; fail=1; fi
}

step "dormancy scan (no load-bearing capability may go dormant)" python3 scripts/ci/dormancy_scan.py
step "integration smoke (un-mocked; skips if :13305 down)" uv run pytest tests/integration/ -q -p no:warnings
if [ "${QUICK}" -eq 0 ]; then
  step "fast unit suite (compound + orchestrator)" uv run pytest tests/compound/ tests/inference/test_orchestrator.py -q -p no:warnings
fi

if [ "${fail}" -ne 0 ]; then
  echo "VERIFY-DEPTH: FAIL"
  exit 1
fi
echo "VERIFY-DEPTH: PASS"
