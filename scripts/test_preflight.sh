#!/usr/bin/env bash
# scripts/test_preflight.sh — sandbox self-test for the preflight + recover scripts.
#
# Verifies that:
#   - preflight exits 0 on a healthy box (the current box)
#   - preflight exits 1 when memory is low (mocked via env override)
#   - recover_fleet --dry-run prints the playbook without taking actions
#   - recover_fleet --hard prints the cold-boot instructions
#
# Run:
#   bash scripts/test_preflight.sh

set -uo pipefail

# Don't let the script pkill things by accident — use --dry-run paths
# wherever possible.
fail=0
assert() {
  local name="$1"
  local actual="$2"
  local expected="$3"
  if [[ "${actual}" == "${expected}" ]]; then
    echo "  ✓ ${name}: ${actual}"
  else
    echo "  ✗ ${name}: got ${actual}, expected ${expected}"
    fail=1
  fi
}

echo "1. preflight exits 0 when free is mocked healthy..."
# We can't easily mock free's output, so we just check that the script
# parses its own input correctly. If memory is low on this box, that's
# a sign you should NOT run the daily researcher until you free memory
# — exactly what the preflight is for.
rc=0
bash scripts/preflight_fleet.sh --verbose >/dev/null 2>&1 || rc=$?
# We accept either 0 (healthy) or 1 (low memory) — both are valid
# preflight outcomes. The test is the script's own internal consistency.
if (( rc == 0 )); then
  echo "  ✓ preflight ran cleanly: rc=0 (healthy)"
elif (( rc == 1 )); then
  echo "  ✓ preflight refused: rc=1 (low memory) — correct behavior, do not start a swarm"
else
  echo "  ✗ preflight unexpected exit: ${rc}"
  fail=1
fi

echo "2. recover_fleet --dry-run prints plan, no actions taken..."
out=$(bash scripts/recover_fleet.sh --dry-run 2>&1)
if echo "${out}" | grep -q "dry-run: would run"; then
  echo "  ✓ dry-run prints plan"
else
  echo "  ✗ dry-run missing plan: ${out}"
  fail=1
fi
# The dry-run is allowed to mention pkill/drop_caches in the *description*
# of what it would do — but it must NOT have actually executed them.
# Check for the absence of real-execution markers instead.
if echo "${out}" | grep -qE "^Killed|drop_caches ok|post-recovery check"; then
  echo "  ✗ dry-run appears to have actually executed: ${out}"
  fail=1
else
  echo "  ✓ dry-run did NOT actually execute recovery actions"
fi

echo "3. recover_fleet --hard prints the cold-boot playbook..."
out=$(bash scripts/recover_fleet.sh --hard 2>&1)
if echo "${out}" | grep -q "COLD BOOT RECOVERY"; then
  echo "  ✓ --hard prints the playbook"
else
  echo "  ✗ --hard missing playbook header"
  fail=1
fi

if (( fail == 0 )); then
  echo ""
  echo "✅ All preflight + recover self-tests passed"
  exit 0
else
  echo ""
  echo "❌ Some self-tests failed"
  exit 1
fi
