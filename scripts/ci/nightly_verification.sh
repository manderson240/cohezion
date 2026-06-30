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

# Integration smoke: the load-bearing live boundary (test_live_loop_smoke.py) SKIPS when the :13305
# OmniRouter is down, but pytest exits 0 either way — so a green here is ambiguous. Surface the skip
# honestly (don't fail the build on it): probe :13305 up-front, and detect a skipped live smoke in the
# pytest output, printing a clear "SMOKE SKIPPED (:13305 down)" notice.
integration_smoke() {
  if ! curl -s --max-time 2 http://localhost:13305/v1/models >/dev/null 2>&1; then
    echo "  -> WARN: :13305 OmniRouter unreachable — live smoke will SKIP (not run)"
  fi
  local out
  out="$(uv run pytest tests/integration/ -q -p no:warnings -rs 2>&1)"
  local rc=$?
  echo "${out}"
  if echo "${out}" | grep -qiE "test_live_loop_smoke.*(SKIPPED|skipped)|SKIPPED.*test_live_loop_smoke"; then
    echo "  -> NOTICE: SMOKE SKIPPED (:13305 down) — un-mocked live boundary did NOT run this cycle"
  elif echo "${out}" | grep -qi "local inference (:13305) down"; then
    echo "  -> NOTICE: SMOKE SKIPPED (:13305 down) — un-mocked live boundary did NOT run this cycle"
  fi
  return ${rc}
}
step "integration smoke (un-mocked; surfaces skip if :13305 down)" integration_smoke
if [ "${QUICK}" -eq 0 ]; then
  step "fast unit suite (compound + orchestrator)" uv run pytest tests/compound/ tests/inference/test_orchestrator.py -q -p no:warnings
fi

if [ "${fail}" -ne 0 ]; then
  echo "VERIFY-DEPTH: FAIL"
  exit 1
fi
echo "VERIFY-DEPTH: PASS"
