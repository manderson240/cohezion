#!/usr/bin/env bash
# =============================================================================
# check_inference_port_bypass.sh — Phase 0b CI guard
#
# Detects live inference paths in src/cohezion/** that bypass the canonical
# lemonade router (:13305) by hard-wiring direct ports :11434 (Ollama) or
# :13306–:13309 (per-port lemonade servers).
#
# EXIT CODES
#   0  — no unallowed violations (or --report mode)
#   1  — violations found (default/fail mode only)
#
# USAGE
#   bash scripts/ci/check_inference_port_bypass.sh            # fail mode (Phase 5+)
#   bash scripts/ci/check_inference_port_bypass.sh --report   # report mode (migration phases 0–4)
#
# ACTIVATION NOTE
#   Phase 3 migration completed 2026-06-12.  TEMPORARY-PHASE2 entries removed.
#   Guard is committed in REPORT mode; flip to fail mode (Phase 5) once all
#   violation counts reach 0 across src/cohezion.  See plan:
#   docs/plans/2026-06-09-lemonade-13305-consolidation.md §Phase 5a.
#
# PATTERN
#   \b(11434|1330[6-9])\b  — word-boundary match (intentionally broader than ":PORT")
#   Rationale: a colon-prefixed pattern misses bare integer defaults such as
#     npu_port: int = 13306   igpu_port: int = 13307   cpu_port: int = 13309
#   which are exactly the Class B direct-tier signatures the guard prevents from
#   re-appearing.  :13305 is excluded because 13305 is NOT in 1330[6-9].
#
# =============================================================================
# ALLOW-LIST
#
# Two tiers:
#
#  ALLOWLIST_PATHS — whole-file/dir prefixes (relative to repo root).
#    Used for files that are dead code, benchmarks, demos, archives, or have
#    an explicit architectural exception.  Each entry is annotated with its
#    reason and migration phase (PERMANENT / PHASE-N / TEMPORARY).
#
#  ALLOWLIST_LINE_PATTERNS — "relpath:regex" pairs.
#    Used when only ONE specific line in an otherwise-migratable file must be
#    retained.  Never whole-file-allow a file just to protect a single line.
#
# Inline override (for future phases): add
#   # allow-direct-port: <reason>
# on any source line to skip that specific line without touching the script.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# ALLOWLIST_PATHS — whole-file/dir prefixes (relative to repo root)
# ---------------------------------------------------------------------------
# Format: "relpath|reason|phase"
#   phase = PERMANENT (never migrate) | TEMPORARY (remove after named phase)
# ---------------------------------------------------------------------------
ALLOWLIST_PATHS=(
    # --- DEAD CODE / BENCHMARK / ARCHIVE (PERMANENT) ---
    # Benchmark file, not import-reachable from production paths
    "src/cohezion/competition/orchestrator/benchmark_ollama_phi4.py|benchmark archive — not import-reachable|PERMANENT"

    # Dead providers per audit; no live callers confirmed
    "src/cohezion/swarm/providers/tip_spear_provider.py|dead provider — no live callers confirmed per 2026-06-09 audit|PERMANENT"
    "src/cohezion/swarm/providers/multi_model_orchestrator.py|dead orchestrator — no live callers confirmed per 2026-06-09 audit|PERMANENT"

    # Hackathon/competition archives — not wired into production paths
    "src/cohezion/competition/gemma_hackathon/|hackathon archive directory — not import-reachable in production|PERMANENT"

    # Simulation benchmark — performance measurement, not live routing
    "src/cohezion/simulations/symphony_max_benchmark.py|simulation benchmark — not live routing code|PERMANENT"

    # direct_tier.py: Phase 3 migrated all defaults to :13305.  Deprecated builders
    # (build_direct_npu_tier / build_direct_igpu_tier / build_direct_cpu_tier) now
    # default to port=13305; no direct-port references remain.  TEMPORARY-PHASE2 entry
    # removed 2026-06-12.

    # inference/health.py: Phase 3 migrated iGPU + CPU probes to :13305.  Retained
    # probes (:13306 NPU historical, :13308 CLaSp permanent) use inline
    # # allow-direct-port: comments.  TEMPORARY-PHASE2 entry removed 2026-06-12.
)

# ---------------------------------------------------------------------------
# ALLOWLIST_LINE_PATTERNS — "relpath:regex" (applied per-line)
# ---------------------------------------------------------------------------
# Format: "relpath_from_root:grep_pattern"
# Use this to protect ONE retained line in an otherwise-migratable file.
# Do NOT whole-file-allow a file just to protect a single line.
# ---------------------------------------------------------------------------
ALLOWLIST_LINE_PATTERNS=(
    # Phase 3 (2026-06-12): triune_orchestrator.py deprecated port params
    # (npu_port=13306, igpu_port=13307, cpu_port=13309, clasp_draft_port=13308)
    # now carry inline # allow-direct-port: comments — handled by is_line_allowed().
    # ALLOWLIST_LINE_PATTERNS entries for triune_orchestrator.py removed.
    # No entries needed here for Phase 3+.
)

# ---------------------------------------------------------------------------
# Script body
# ---------------------------------------------------------------------------

REPORT_MODE=false
if [[ "${1:-}" == "--report" ]]; then
    REPORT_MODE=true
fi

# Derive repo root from git — never hardcode /home/...
REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
SRC_DIR="${REPO_ROOT}/src/cohezion"

if [[ ! -d "${SRC_DIR}" ]]; then
    echo "ERROR: src/cohezion not found at ${SRC_DIR}" >&2
    exit 2
fi

# Build grep pattern
PATTERN='\b(11434|1330[6-9])\b'

# ---------------------------------------------------------------------------
# Helper: check if a relative file path is in the whole-file allow-list
# ---------------------------------------------------------------------------
is_path_allowed() {
    local relpath="$1"
    for entry in "${ALLOWLIST_PATHS[@]}"; do
        local prefix="${entry%%|*}"
        # Prefix match: if the relpath starts with prefix, it's allowed
        if [[ "${relpath}" == "${prefix}"* ]]; then
            return 0
        fi
    done
    return 1
}

# ---------------------------------------------------------------------------
# Helper: check if a specific line in a file is in ALLOWLIST_LINE_PATTERNS
# ---------------------------------------------------------------------------
is_line_allowed() {
    local relpath="$1"
    local line_content="$2"
    for entry in "${ALLOWLIST_LINE_PATTERNS[@]}"; do
        local entry_path="${entry%%:*}"
        local entry_pattern="${entry#*:}"
        if [[ "${relpath}" == "${entry_path}" ]]; then
            if echo "${line_content}" | grep -qE "${entry_pattern}"; then
                return 0
            fi
        fi
    done
    # Also honor inline override comment in the source line itself
    if echo "${line_content}" | grep -q '# allow-direct-port:'; then
        return 0
    fi
    return 1
}

# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------
violations=()
raw_match_count=0

while IFS= read -r match_line; do
    # match_line format:  path/to/file.py:42:    some_code = 13306
    filepath="${match_line%%:*}"
    rest="${match_line#*:}"
    lineno="${rest%%:*}"
    content="${rest#*:}"

    raw_match_count=$(( raw_match_count + 1 ))

    # Convert absolute path to relative (from repo root)
    relpath="${filepath#${REPO_ROOT}/}"

    # Check whole-file allow-list
    if is_path_allowed "${relpath}"; then
        continue
    fi

    # Check line-level allow-list
    if is_line_allowed "${relpath}" "${content}"; then
        continue
    fi

    violations+=("${relpath}:${lineno}: ${content}")
done < <(grep -rn --include="*.py" -E "${PATTERN}" "${SRC_DIR}" 2>/dev/null)

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
violation_count="${#violations[@]}"

echo "check_inference_port_bypass: raw matches=${raw_match_count}, post-allowlist violations=${violation_count}"
echo ""

if [[ ${violation_count} -gt 0 ]]; then
    echo "VIOLATIONS (files that bypass :13305 router without allow-list exception):"
    for v in "${violations[@]}"; do
        echo "  ${v}"
    done
    echo ""
    echo "To suppress: add the file to ALLOWLIST_PATHS with a documented reason, or add"
    echo "  # allow-direct-port: <reason>"
    echo "on the specific line. See docs/plans/2026-06-09-lemonade-13305-consolidation.md"
    echo "for the migration plan."
    echo ""

    if [[ "${REPORT_MODE}" == "true" ]]; then
        echo "STATUS: report mode -- violations listed above, exiting 0 (build not blocked)"
        echo "Flip to fail mode in Phase 5 by removing --report from CI invocation."
        exit 0
    else
        echo "STATUS: fail mode -- ${violation_count} violation(s) block the build."
        exit 1
    fi
else
    echo "STATUS: no violations -- all local inference paths route through :13305 (or are allow-listed)."
    exit 0
fi
