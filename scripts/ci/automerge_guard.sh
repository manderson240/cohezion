#!/usr/bin/env bash
# scripts/ci/automerge_guard.sh — automated PR landing guard for Cohezion.
#
# This script automates the manual process we did during the consolidation campaign:
#   1. Run all CI gates locally (format, lint ratchet, unit tests, import smoke, inference tests)
#   2. If all pass → merge the PR via gh CLI
#   3. If any fail → print a structured report and exit non-zero
#   4. Log the result to SurrealDB for provenance
#
# Usage:
#   scripts/ci/automerge_guard.sh <PR_NUMBER>
#   scripts/ci/automerge_guard.sh 252
#
# Exit codes:
#   0 = all gates passed, PR merged
#   1 = one or more gates failed, PR not merged
#   2 = CI checks still pending (retry later)
#   3 = error (bad PR number, gh not installed, etc.)

set -uo pipefail
cd "$(dirname "$0")/../.." || exit 3

PR_NUMBER="${1:?Usage: $0 <PR_NUMBER>}"
FAIL=0
GATES_PASSED=()
GATES_FAILED=()

step() {
  local name="$1"; shift
  echo "== ${name} =="
  if "$@"; then
    echo "  -> PASS"
    GATES_PASSED+=("$name")
  else
    echo "  -> FAIL"
    GATES_FAILED+=("$name")
    FAIL=1
  fi
}

echo "=== AutoMerge Guard for PR #${PR_NUMBER} ==="
echo "Time: $(date -Iseconds)"
echo ""

# Step 0: Check out the PR branch
echo "[0] Fetching PR #${PR_NUMBER}..."
gh pr checkout "$PR_NUMBER" 2>/dev/null || {
  echo "  -> ERROR: could not checkout PR #${PR_NUMBER}"
  exit 3
}

# Step 1: Ruff format check
step "ruff format --check" uv run ruff format --check src/ tests/

# Step 2: Ruff lint check
step "ruff lint check" uv run ruff check src/ tests/

# Step 3: Ruff debt ratchet (gating)
step "ruff debt ratchet" uv run python scripts/ci/ruff_ratchet.py

# Step 4: Unit tests (gating)
step "unit tests" uv run pytest tests/unit/ -q --tb=short -p no:warnings

# Step 5: Import smoke test
step "import smoke test" uv run pytest tests/unit/test_import_smoke.py -q --tb=short -p no:warnings

# Step 6: Inference tests (gating — but live tests skip without Lemonade)
step "inference tests" uv run pytest tests/inference/ -q --tb=short -p no:warnings

# Step 6b: Local-LLM choke-point. Flags NET-NEW raw chat/completions call sites
# that bypass the blessed path + its content->reasoning_content fallback.
# Report-mode-first rollout (mirrors check_inference_port_bypass.sh) — always
# exits 0 for now; drop the --report flag to enforce (fail on new sites) once
# the baseline is settled on the branch.
step "local-llm choke-point" bash scripts/ci/check_local_llm_chokepoint.sh --report

# Step 7: Conventional commit / version governance
step "version governance" uv run python scripts/ci/version_governance.py

# Report
echo ""
echo "=== Summary ==="
echo "Passed: ${#GATES_PASSED[@]} gates"
for g in "${GATES_PASSED[@]}"; do echo "  ✓ $g"; done
echo "Failed: ${#GATES_FAILED[@]} gates"
for g in "${GATES_FAILED[@]}"; do echo "  ✗ $g"; done

if [ "$FAIL" -eq 0 ]; then
  echo ""
  echo "=== All gates passed — merging PR #${PR_NUMBER} ==="
  gh pr merge "$PR_NUMBER" --squash --admin --delete-branch 2>/dev/null
  merge_result=$?
  if [ $merge_result -eq 0 ]; then
    echo "✅ PR #${PR_NUMBER} merged successfully."
    # Log to SurrealDB
    curl -s -X POST http://localhost:8001/sql \
      -H "Content-Type: text/plain" -u "root:root" \
      -H "Surreal-NS: cohezion" -H "Surreal-DB: main" \
      -d "CREATE automerge_log:{{time::now()}} CONTENT {
        \"pr\": \"#${PR_NUMBER}\",
        \"status\": \"merged\",
        \"gates_passed\": $(printf '%s\n' "${GATES_PASSED[@]}" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))"),
        \"timestamp\": time::now()
      };" 2>/dev/null | head -1
    exit 0
  else
    echo "❌ Merge failed (exit $merge_result). PR may have conflicts or be blocked."
    exit 1
  fi
else
  echo ""
  echo "❌ ${#GATES_FAILED[@]} gate(s) failed — PR #${PR_NUMBER} not merged."
  # Log to SurrealDB
  curl -s -X POST http://localhost:8001/sql \
    -H "Content-Type: text/plain" -u "root:root" \
    -H "Surreal-NS: cohezion" -H "Surreal-DB: main" \
    -d "CREATE automerge_log:{{time::now()}} CONTENT {
      \"pr\": \"#${PR_NUMBER}\",
      \"status\": \"blocked\",
      \"gates_failed\": $(printf '%s\n' "${GATES_FAILED[@]}" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))"),
      \"timestamp\": time::now()
    };" 2>/dev/null | head -1
  exit 1
fi