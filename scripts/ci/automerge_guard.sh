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
#
# ENFORCING as of 2026-07-28 (was --report). The report-mode rollout is over: the
# baseline was settled at 77 files and the gate now FAILS on any net-new bypass.
#
# Why this matters for quarter-on-a-string: a raw urllib/httpx call to :13305 cannot
# be routed (no local-first cascade), cannot be ledgered (TL1/TL2 record_local vs
# record_cloud), and cannot be gated. Even when such a call is local-only today, it
# is an un-instrumented seam through which a cloud escalation can later appear
# unobserved — `data_mesh/land_runner.py` already documents "escalate to cloud on a
# flag" from exactly such a raw call site.
#
# The three files baselined at the flip (prompt_reliability.py, land_runner.py,
# session_digest.py) are all local-only $0 today. They are GRANDFATHERED, not
# absolved — each still needs routing through the blessed path.
#
# To add a call site intentionally: scripts/ci/check_local_llm_chokepoint.sh --update-baseline
step "local-llm choke-point" bash scripts/ci/check_local_llm_chokepoint.sh

# Step 6c: Dormancy scan (gating). A curated registry of load-bearing capabilities
# that must have a production consumer, not just a `def` + green unit tests — the
# failure class that let the regression gate, jepa_coherence, and the FAPO
# failure-path wiring all sit dormant behind passing tests. Unlike 6b, this is
# blocking from the start: the registry is curated specifically to never cry wolf.
step "dormancy scan" uv run python scripts/ci/dormancy_scan.py

# Step 6d: Referential integrity — systemd units. Does every ExecStart target actually resolve?
# Added 2026-07-26 after 5 of 45 user units were found pointing at things that do not exist (one
# shipped `__PYTHON3__` installer placeholders verbatim), producing ~10k journal failure events in
# 24h that nothing surfaced. Handles BOTH the absolute-path form and `python -m pkg.module` — the
# latter is what broke cohezion-resource-guard and is invisible to a naive path check.
# Report-mode-first (mirrors 6b): the 5 known-broken units are pre-existing. Drop --report to
# enforce once they are wired or retired, so the class cannot silently return.
step "systemd unit audit" uv run python scripts/ci/systemd_unit_audit.py --report

# Step 6e: Referential integrity — graph cardinality. Are DECLARED relation tables populated?
# Same instrument class as 6d (existence + cardinality over declarations), different referent type.
# 8 of 9 declared relation tables are empty and `journey_knowledge` — the bridge between 278,741
# execution rows and 1,146 knowledge docs — holds 0 rows; nothing in ~30 existing gates could
# notice. Report-only until the tables are populated or the declarations retired.
step "graph cardinality" uv run python scripts/ci/graph_cardinality_audit.py

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