#!/usr/bin/env bash
# Local-LLM chat choke-point guard.
#
# Every local-LLM chat call SHOULD route through a BLESSED path (see
# BLESSED_CALLERS below — today cohezion.inference.gauntlet._call_model, a
# successor helper may come later) which encodes the recurrence-critical safety
# contract:
#   1. content -> reasoning_content fallback (a reasoning model that exhausts its
#      budget mid-think leaves message.content == "" — read reasoning_content)
#   2. strip inline <think>...</think>
#   3. never raise on error (keeps batch loops alive)
# Consumption guidance (canonical, single source of truth):
#   ~/vaults/cohezion-vault/model-research/2026-07-17-thinking-models-playbook.md
#
# A brand-new raw httpx/requests/urllib POST to .../chat/completions that skips
# the blessed path is how a solved trap re-appears (2026-07-17 graphify
# empty-content incident: a new urllib call site that dropped the
# reasoning_content fallback and returned empty; already remediated). This guard
# flags NET-NEW raw call sites; it does NOT migrate the pre-existing sites in one
# pass (harness N4 lesson — not all legacy sites are bugs; a wholesale refactor
# is a separate, permission-gated track).
#
# Baseline is keyed on FILE (not file:line) on purpose — line numbers churn on
# every edit, but the set of offending files is stable and a new module trips it
# immediately. Rebuild it intentionally with --update-baseline after a new call
# site has been reviewed (or one removed).
#
# Scope (constraint from team-lead 2026-07-17):
#   - ENFORCEABLE: src/cohezion/** + scripts/**  (SCAN_ROOTS)
#   - REPORT-ONLY: ~/cohezion-labs (LABS_ROOT) — slated for dissolution under
#     refactor Phase 3 (~126 scripts); listed for visibility, never allowlisted
#     per-file and never affects exit code.
#
# Usage (report-mode-first rollout, mirroring check_inference_port_bypass.sh):
#   check_local_llm_chokepoint.sh --report            always exits 0; prints new sites + labs listing
#   check_local_llm_chokepoint.sh                      fails (exit 1) on any new enforceable file
#   check_local_llm_chokepoint.sh --update-baseline    rewrite baseline from current tree

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Deterministic byte-wise collation so sort/comm agree regardless of the
# caller's locale (comm requires both inputs sorted under the SAME collation).
export LC_ALL=C

# Blessed call path(s): repo-relative files exempt from the guard because they
# ARE the reference implementation of the safety contract. Relocating the choke
# point to a successor module = edit this one array.
BLESSED_CALLERS=(
  "src/cohezion/inference/gauntlet.py"
)
# The guard's own tooling legitimately contains the literal "chat/completions"
# for detection purposes — it is not a call site.
GUARD_TOOLING=(
  "scripts/ci/_chat_chokepoint_ast_filter.py"
  "scripts/ci/check_local_llm_chokepoint.sh"
)

SCAN_ROOTS="${SCAN_ROOTS:-src/cohezion scripts}"
LABS_ROOT="${LABS_ROOT:-$HOME/cohezion-labs}"
BASELINE="scripts/ci/chat_chokepoint_baseline.txt"
FILTER="$(dirname "${BASH_SOURCE[0]}")/_chat_chokepoint_ast_filter.py"

MODE="check"
case "${1:-}" in
  --report) MODE="report" ;;
  --update-baseline) MODE="update" ;;
  "") MODE="check" ;;
  *) echo "unknown arg: $1" >&2; exit 2 ;;
esac

# 1. grep raw chat/completions mentions in the enforceable roots, minus blessed
#    path, guard tooling, and tests; 2. comment/docstring-aware filter -> real
#    call sites; 3. reduce to unique files.
collect_enforceable_files() {
  local hits
  hits="$(grep -rnE "chat/completions" $SCAN_ROOTS --include="*.py" 2>/dev/null \
    | grep -vE "/tests?/|_test\.py|test_" || true)"
  local f
  for f in "${BLESSED_CALLERS[@]}" "${GUARD_TOOLING[@]}"; do
    hits="$(printf '%s\n' "$hits" | grep -vF "$f" || true)"
  done
  printf '%s' "$hits" | python3 "$FILTER" | cut -d: -f1 | sort -u | sed '/^$/d'
}

current_files="$(collect_enforceable_files)"

if [[ "$MODE" == "update" ]]; then
  printf '%s\n' "$current_files" | sed '/^$/d' > "$BASELINE"
  n="$(grep -c . "$BASELINE" || echo 0)"
  echo "Baseline rewritten: $n enforceable files with raw chat/completions call sites -> $BASELINE"
  exit 0
fi

baseline_files=""
[[ -f "$BASELINE" ]] && baseline_files="$(sed '/^$/d' "$BASELINE" | sort -u)"

# new = current \ baseline
new_files="$(comm -23 <(printf '%s\n' "$current_files" | sed '/^$/d' | sort -u) \
                      <(printf '%s\n' "$baseline_files" | sed '/^$/d' | sort -u) || true)"

new_count=0
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  echo "NEW raw chat/completions call site outside blessed path: $f"
  new_count=$((new_count + 1))
done <<< "$new_files"

# Report-only labs listing (never affects exit; not baselined per-file).
if [[ "$MODE" == "report" && -d "$LABS_ROOT" ]]; then
  echo "--- report-only: ~/cohezion-labs raw chat/completions files (NOT enforced) ---"
  labs_files="$(grep -rlE "chat/completions" "$LABS_ROOT" --include="*.py" 2>/dev/null \
    | grep -vE "/\.venv/|/site-packages/|/node_modules/" | sort -u || true)"
  labs_n="$(printf '%s\n' "$labs_files" | sed '/^$/d' | grep -c . || echo 0)"
  printf '%s\n' "$labs_files" | sed '/^$/d' | sed 's/^/  labs: /'
  echo "  (labs files with raw calls: $labs_n — slated for Phase 3 dissolution)"
fi

echo "---"
echo "Enforceable baseline files: $(printf '%s\n' "$baseline_files" | sed '/^$/d' | grep -c . || echo 0) | new (unbaselined): $new_count"

if [[ "$MODE" == "report" ]]; then
  exit 0
fi
if [[ "$new_count" -gt 0 ]]; then
  echo "FAIL: new local-LLM chat call site(s) bypass the blessed choke-point." >&2
  echo "Route through a BLESSED_CALLERS path (content->reasoning_content fallback +" >&2
  echo "<think> strip), or if intentional run --update-baseline after review." >&2
  exit 1
fi
exit 0
