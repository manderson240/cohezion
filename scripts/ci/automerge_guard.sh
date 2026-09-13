#!/usr/bin/env bash
# scripts/ci/automerge_guard.sh — automated PR landing guard for Cohezion.
#
# This script automates the manual process we did during the consolidation campaign:
#   1. Run all CI gates locally (format, lint ratchet, unit tests, import smoke, inference tests)
#   2. If all pass → merge the PR via gh CLI
#   3. If any fail → print a structured report and exit non-zero
#   4. Log the result to SurrealDB for provenance
#
# Landing discipline (bors "not-rocket-science" rule, added 2026-09-09):
#   - Gates are validated against a TEMP INTEGRATION WORKTREE = PR merged on top
#     of tip-of-trunk, never against stale HEAD — and never inside the user's
#     working copy, so a dirty worktree (submodules, untracked artifacts) cannot
#     abort or poison the validation. A PR whose merge conflicts with main fails
#     here with "rebase needed" instead of dirtying main.
#   - Before merging, trunk is re-fetched; if main moved since validation, the
#     guard exits 2 (retry later) rather than merging something it didn't validate.
#   - A flock serializes landings: one PR in flight at a time (poor-man's queue
#     for a single maintainer; research digest 2026-09-09, pillar P1).
#   - Attribution gates (pillar P2): a failing gate blocks the landing only if
#     it ALSO passes on a pristine trunk-tip control worktree — i.e. only if
#     THIS PR broke it. Pre-existing trunk debt is logged (SurrealDB
#     `trunk_debt`) and surfaced in the summary, but never blocks a clean PR.
#
# Usage:
#   scripts/ci/automerge_guard.sh <PR_NUMBER>
#   scripts/ci/automerge_guard.sh 252
#
# Exit codes:
#   0 = all gates passed, PR merged
#   1 = one or more gates failed, or PR conflicts with main (rebase needed)
#   2 = CI checks pending / trunk moved during validation / another guard running (retry later)
#   3 = error (bad PR number, gh not installed, etc.)

set -uo pipefail
cd "$(dirname "$0")/../.." || exit 3

PR_NUMBER="${1:?Usage: $0 <PR_NUMBER>}"
FAIL=0
GATES_PASSED=()
GATES_FAILED=()
TRUNK_DEBT=()

# Serialize landings: one PR through the guard at a time (poor-man's merge queue).
mkdir -p /tmp/cohezion-automerge
exec 9>/tmp/cohezion-automerge/lock
if ! flock -n 9; then
  echo "❌ Another automerge_guard is running (lock held). Retry later."
  exit 2
fi

# Remember where the user's checkout lives; all final actions run from there.
ORIG_DIR="$(pwd)"

step() {
  local name="$1"; shift
  echo "== ${name} =="
  if "$@"; then
    echo "  -> PASS"
    GATES_PASSED+=("$name")
  else
    # Attribution gate (research digest P2): a failing gate blocks the landing
    # only if the PR made it WORSE than trunk. Re-run the same command in the
    # pristine trunk-tip control worktree; failure there too = pre-existing
    # trunk debt — logged, but not attributed to this PR.
    control_out="$(cd "$CONTROL_WORKTREE" && "$@" 2>&1)"
    control_status=$?
    if [ "$control_status" -eq 0 ]; then
      echo "  -> FAIL (introduced by this PR — blocks landing)"
      GATES_FAILED+=("$name")
      FAIL=1
    else
      echo "  -> TRUNK-DEBT (also fails on pristine trunk tip — not introduced by this PR)"
      TRUNK_DEBT+=("$name")
    fi
  fi
}

step_advisory() {
  local name="$1"; shift
  echo "== ${name} =="
  if "$@"; then
    echo "  -> PASS"
    GATES_PASSED+=("$name")
  else
    echo "  -> ADVISORY (ignored)"
    GATES_PASSED+=("${name} (advisory)")
  fi
}

echo "=== AutoMerge Guard for PR #${PR_NUMBER} ==="
echo "Time: $(date -Iseconds)"
echo ""

# Step 0: Bors-rule validation base — gates run in a THROWAWAY WORKTREE holding
# a temp integration branch (origin/main + PR), never on the PR's stale HEAD and
# never inside the user's working copy (dirty uncommitted state would otherwise
# abort the merge — the exact failure the first live run hit). A PR that conflicts
# with trunk fails HERE instead of dirtying main after a blind merge.
echo "[0] Fetching trunk tip and PR #${PR_NUMBER}..."
git fetch origin main --quiet || { echo "  -> ERROR: git fetch origin main failed"; exit 3; }
TRUNK_TIP="$(git rev-parse origin/main)" || { echo "  -> ERROR: cannot resolve origin/main"; exit 3; }

PR_SHA="$(gh pr view "$PR_NUMBER" --json headRefOid --jq .headRefOid)" || {
  echo "  -> ERROR: could not resolve head of PR #${PR_NUMBER}"
  exit 3
}
echo "  -> PR head: ${PR_SHA:0:7}, trunk tip: ${TRUNK_TIP:0:7}"

INTEG_BRANCH="automerge-integ-${PR_NUMBER}"
WORKTREE="/tmp/cohezion-automerge/integ-${PR_NUMBER}"
git worktree remove --force "$WORKTREE" 2>/dev/null
git branch -D "$INTEG_BRANCH" 2>/dev/null
rm -rf "$WORKTREE"
if ! git worktree add -q "$WORKTREE" -b "$INTEG_BRANCH" "$TRUNK_TIP" 2>/dev/null; then
  echo "  -> ERROR: cannot create integration worktree at ${WORKTREE}"
  exit 3
fi
cd "$WORKTREE" || exit 3
if ! MERGE_OUT="$(git merge --no-ff --no-edit "$PR_SHA")" 2>/dev/null; then
  git merge --abort 2>/dev/null
  cd "$ORIG_DIR"
  git worktree remove --force "$WORKTREE" 2>/dev/null
  git branch -D "$INTEG_BRANCH" 2>/dev/null
  echo "  -> ❌ PR #${PR_NUMBER} does not merge cleanly onto origin/main (${TRUNK_TIP:0:7})."
  [ -n "$MERGE_OUT" ] && echo "$MERGE_OUT" | head -10
  echo "     Rebase the branch onto main and re-run the guard. Nothing was merged."
  exit 1
fi
echo "  -> Integration worktree ready: trunk ${TRUNK_TIP:0:7} + PR ${PR_SHA:0:7}"

# Pristine trunk-tip control worktree — the attribution baseline. Gates that fail
# on the integration tree are re-run here: failing here too means the debt was
# already on trunk (not introduced by this PR).
CONTROL_WORKTREE="/tmp/cohezion-automerge/control-${PR_NUMBER}"
git worktree remove --force "$CONTROL_WORKTREE" 2>/dev/null
rm -rf "$CONTROL_WORKTREE"
if ! git worktree add -q "$CONTROL_WORKTREE" "$TRUNK_TIP" 2>/dev/null; then
  echo "  -> ERROR: cannot create trunk control worktree at ${CONTROL_WORKTREE}"
  exit 3
fi

# Step 1: Ruff format check
step "ruff format --check" uv run ruff format --check src/ tests/

# Step 2: Ruff lint check (advisory per AGENTS.md — ruff debt ratchet is the blocking gate)
step_advisory "ruff lint check" uv run ruff check src/ tests/

# Step 3: Ruff debt ratchet (gating)
step "ruff debt ratchet" uv run python scripts/ci/ruff_ratchet.py

# Step 3b: Mypy debt ratchet. --self-test first, same reason as the other scanners:
# a broken ratchet otherwise reads as a clean "no new type debt". The self-test also
# covers the abort case — a crashed mypy prints "Found 1 error", and counting that
# would ratchet the baseline down to 1 and silently retire the gate — and the
# coverage case, where a widened `exclude` lowers the count by checking fewer files.
step "mypy ratchet self-test" uv run python scripts/ci/mypy_ratchet.py --self-test
step "mypy debt ratchet" uv run python scripts/ci/mypy_ratchet.py


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
# --self-test FIRST: it proves the scanner can still FAIL (with a guaranteed-dormant
# sentinel + known-wired capability). A scanner bug otherwise reads as a clean 0 errors.
step "dormancy self-test" uv run python scripts/ci/dormancy_scan.py --self-test
step "dormancy scan" uv run python scripts/ci/dormancy_scan.py

# Step 6c-bis: Doc↔code drift — the sibling of 6c. dormancy_scan asks "does this code have a
# consumer?"; this asks "do the docs tell the truth about the code?". Already gating in
# ci.yml; added here 2026-07-29 so the LOCAL landing gate matches CI rather than discovering
# the failure after a push. --self-test runs FIRST: it proves each check can still FAIL (with
# a negative control that must stay silent). A scanner bug otherwise reads as a clean "0
# errors" — how the RGA1/RGA2 phantom invariants passed, and how E2 was found unable to fire.
step "doc-code self-test" uv run python scripts/ci/doc_code_consistency.py --self-test
step "doc-code consistency" uv run python scripts/ci/doc_code_consistency.py

# Step 6c-ter: Phantom attribute reads — the THIRD sibling. 6c asks "does this capability have a
# consumer?", 6c-bis asks "do the docs tell the truth?", this asks "does the attribute this code
# reads actually exist?". Added 2026-08-26 after `getattr(result, "error", "")` in
# actioner/engine.py was found reading a field ExecutionResult does not have (9 constructions in
# executor.py, 0 pass error=), so EVERY failure recorded an empty reason and a fully-blocked
# compound pipeline was indistinguishable from a slow one for weeks. mypy cannot catch it:
# getattr with a literal + default is deliberate dynamism whose contract IS to succeed silently.
# --self-test first, same reason as 6c-bis: a scanner bug otherwise reads as a clean "0 errors".
# Validated against the real pre-fix tree from git history (dee080d0c~1): fires on the historical
# defect, silent on the fix.
step "phantom-attr self-test" uv run python scripts/ci/phantom_attr_scan.py --self-test
step "phantom-attr scan" uv run python scripts/ci/phantom_attr_scan.py

# Step 6c-ter-bis: unrestricted exec/eval (security finding H5). CPython auto-injects the FULL
# builtins into a globals dict lacking "__builtins__", so exec(llm_code, {}) reaches
# __import__/open/eval. safe_exec_globals() closed the 2026-06 instances, yet 2026-09-13 found 13
# unrestricted sites in src/ (5 running LLM output) because nothing re-checked. Exceptions need
# an inline "# unrestricted-exec-ok: <reason>" pragma. --self-test first (sibling rationale).
step "unrestricted-exec self-test" uv run python scripts/ci/unrestricted_exec_scan.py --self-test
step "unrestricted-exec scan" uv run python scripts/ci/unrestricted_exec_scan.py

# Step 6c-quater: META-gate. The scans above ask questions about the CODE; this asks whether
# the gates themselves can still answer. It RUNS each gate's --self-test rather than
# checking the flag exists, because doc_code_consistency.py was found shipping a
# --self-test that printed "BROKEN -- a check cannot fail" and exited 1 while satisfying
# any substring check. Scope is derived from what CI invokes, so the rule attaches by
# itself when a script becomes a gate.
step "gate self-test coverage (self-test)" uv run python scripts/ci/self_test_coverage.py --self-test
step "gate self-test coverage" uv run python scripts/ci/self_test_coverage.py

# Step 6d: Referential integrity — systemd units. Does every ExecStart target actually resolve?
# Added 2026-07-26 after 5 of 45 user units were found pointing at things that do not exist (one
# shipped `__PYTHON3__` installer placeholders verbatim), producing ~10k journal failure events in
# 24h that nothing surfaced. Handles BOTH the absolute-path form and `python -m pkg.module` — the
# latter is what broke cohezion-resource-guard and is invisible to a naive path check.
# Report-mode-first (mirrors 6b): the 5 known-broken units are pre-existing. Drop --report to
# enforce once they are wired or retired, so the class cannot silently return.
# Step 6d/e: Referential integrity
if [ -f scripts/ci/systemd_unit_audit.py ]; then
  step "systemd unit audit" uv run python scripts/ci/systemd_unit_audit.py
fi

if [ -f scripts/ci/graph_cardinality_audit.py ]; then
  step "graph cardinality" uv run python scripts/ci/graph_cardinality_audit.py
fi

if [ -f scripts/ci/producer_consumer_audit.py ]; then
  step "producer-consumer self-test" uv run python scripts/ci/producer_consumer_audit.py --self-test
  step "producer-consumer audit" uv run python scripts/ci/producer_consumer_audit.py
fi

# Step 7: Conventional commit / version governance
step "version governance" uv run python scripts/ci/version_governance.py

# Report
echo ""
echo "=== Summary ==="
echo "Passed: ${#GATES_PASSED[@]} gates"
for g in "${GATES_PASSED[@]}"; do echo "  ✓ $g"; done
echo "Failed: ${#GATES_FAILED[@]} gate(s) introduced by this PR"
for g in "${GATES_FAILED[@]}"; do echo "  ✗ $g"; done
echo "Trunk debt (pre-existing, not blocking): ${#TRUNK_DEBT[@]} gate(s)"
for g in "${TRUNK_DEBT[@]}"; do echo "  ⚠ $g"; done

if [ "$FAIL" -eq 0 ]; then
  # Stale-trunk check: if main moved while gates ran, what we validated is not
  # what would land. Retry (the next run re-validates against the new tip).
  git fetch origin main --quiet
  TRUNK_NOW="$(git rev-parse origin/main)"
  git worktree remove --force "$WORKTREE" 2>/dev/null
  git worktree remove --force "$CONTROL_WORKTREE" 2>/dev/null
  git branch -D "$INTEG_BRANCH" 2>/dev/null
  cd "$ORIG_DIR" || exit 3
  if [ "$TRUNK_NOW" != "$TRUNK_TIP" ]; then
    echo ""
    echo "⚠️  Trunk moved during validation (${TRUNK_TIP:0:7} → ${TRUNK_NOW:0:7})."
    echo "   Gates validated a base that is no longer tip — re-run the guard to re-validate."
    exit 2
  fi
  echo ""
  echo "=== All gates passed — merging PR #${PR_NUMBER} ==="
  # NOTE: no --admin. AGENTS.md forbids bypassing gates; main has no required
  # checks, so a plain squash merge is the honest landing path.
  merge_out="$(gh pr merge "$PR_NUMBER" --squash --delete-branch 2>&1)"
  merge_result=$?
  if [ $merge_result -eq 0 ]; then
    echo "✅ PR #${PR_NUMBER} merged successfully."
    # Log to SurrealDB — trunk_debt records gates that failed on BOTH trees
    # (pre-existing debt surface, feeds the P2 attribution ratchet over time)
    curl -s -X POST http://localhost:8001/sql \
      -H "Content-Type: text/plain" -u "root:root" \
      -H "Surreal-NS: cohezion" -H "Surreal-DB: main" \
      -d "CREATE automerge_log CONTENT {
        \"pr\": \"#${PR_NUMBER}\",
        \"status\": \"merged\",
        \"gates_passed\": $(printf '%s\n' "${GATES_PASSED[@]}" | uv run python -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))"),
        \"trunk_debt\": $(printf '%s\n' "${TRUNK_DEBT[@]}" | uv run python -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))"),
        \"timestamp\": time::now()
      };" 2>/dev/null | head -1
    exit 0
  else
    echo "❌ Merge failed (exit $merge_result). PR may have conflicts or be blocked."
    [ -n "$merge_out" ] && echo "$merge_out"
    exit 1
  fi
else
  echo ""
  echo "❌ ${#GATES_FAILED[@]} gate(s) introduced by this PR — landing blocked."
  git worktree remove --force "$WORKTREE" 2>/dev/null
  git worktree remove --force "$CONTROL_WORKTREE" 2>/dev/null
  git branch -D "$INTEG_BRANCH" 2>/dev/null
  cd "$ORIG_DIR" || exit 3
  # Log to SurrealDB — attribution record: which gates the PR broke, which were already broken on trunk
  curl -s -X POST http://localhost:8001/sql \
    -H "Content-Type: text/plain" -u "root:root" \
    -H "Surreal-NS: cohezion" -H "Surreal-DB: main" \
    -d "CREATE automerge_log CONTENT {
      \"pr\": \"#${PR_NUMBER}\",
      \"status\": \"blocked\",
      \"gates_failed\": $(printf '%s\n' "${GATES_FAILED[@]}" | uv run python -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))"),
      \"trunk_debt\": $(printf '%s\n' "${TRUNK_DEBT[@]}" | uv run python -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))"),
      \"timestamp\": time::now()
    };" 2>/dev/null | head -1
  exit 1
fi