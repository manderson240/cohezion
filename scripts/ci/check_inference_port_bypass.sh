#!/usr/bin/env bash
# CB/N4 guard: flag direct references to hardcoded per-lane Lemonade dispatch
# ports (13306 NPU, 13307/13308 iGPU, 13309 CPU) outside the single :13305
# OmniRouter path. See ~/.claude/rules/harness.md N4.
#
# Recreated 2026-07-06: harness.md referenced this script and a `clasp_tier.py`
# allow-list entry, but neither existed anywhere in the repo — this is a fresh,
# honest rebuild using only allow-list entries that are actually present today
# (direct_tier.py, health.py, the N2-retained cpu_port line in
# triune_orchestrator.py). Report mode only — the violation count is nowhere
# near zero, so fail mode would be dishonest; migration status unverified.
#
# 2026-07-10 (F2 phase 1, per vault triage
# research/2026-07-10-f2-port-bypass-triage.md):
#   - `11434` (Ollama) was dropped from PATTERN entirely. Root CLAUDE.md
#     documents Ollama as a first-class, actively-maintained local backend
#     ("Global limit = 4 concurrent") — it is not a dead Lemonade lane, so
#     flagging it here was a category error, not a real bypass. This guard's
#     job is hardcoded per-lane *Lemonade* dispatch that bypasses :13305;
#     Ollama traffic is out of scope by policy. (55 of 149 prior raw hits.)
#   - The guard is now comment/docstring-aware via _port_bypass_ast_filter.py:
#     a `1330[6-9]` occurrence inside a `#` comment or a bare string-literal
#     docstring (module/class/function/inline banner table) is prose about
#     the topology, not a dispatch bypass — grep alone can't tell the two
#     apart. Fails open (flags the line) if a file won't parse. (49 of 149
#     prior raw hits were this kind of false positive, though a few
#     port-numbers-in-prose lines embedded in real code strings — e.g. a
#     dict `"note": (...)` value — are NOT comments/docstrings syntactically
#     and still correctly flag; see the triage doc's residual-count note.)
#
# Usage:
#   check_inference_port_bypass.sh --report   always exits 0, prints findings
#   check_inference_port_bypass.sh            fails (exit 1) if any violation found

set -euo pipefail

REPORT_ONLY=false
if [[ "${1:-}" == "--report" ]]; then
  REPORT_ONLY=true
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PATTERN='\b1330[6-9]\b'

candidates=""
while IFS=: read -r file line content; do
  # Inline per-line override
  if [[ "$content" == *"# allow-direct-port:"* ]]; then
    continue
  fi
  # Path-based allow-list: confirmed-real exception files/dirs
  case "$file" in
    *dead/*|*benchmark*|*demo*|*archive*) continue ;;
    */competition/*/kaggle_submission.py) continue ;;
    src/cohezion/inference/direct_tier.py) continue ;;
    src/cohezion/inference/health.py) continue ;;
  esac
  # File-specific single-line allow: N2-retained cpu_port default
  if [[ "$file" == "src/cohezion/inference/triune_orchestrator.py" ]] && [[ "$content" == *"cpu_port: int = 13309"* ]]; then
    continue
  fi
  candidates+="$file:$line:$content"$'\n'
done < <(grep -rnE "$PATTERN" src/cohezion/ --include="*.py" || true)

violations=0
while IFS= read -r hit; do
  [[ -z "$hit" ]] && continue
  echo "$hit"
  violations=$((violations + 1))
done < <(printf '%s' "$candidates" | python3 "$(dirname "${BASH_SOURCE[0]}")/_port_bypass_ast_filter.py")

echo "---"
echo "Total violations (post-allow-list): $violations"

if [[ "$REPORT_ONLY" == true ]]; then
  exit 0
fi

if [[ "$violations" -gt 0 ]]; then
  echo "FAIL: direct port bypass found outside the :13305 OmniRouter path." >&2
  exit 1
fi
exit 0
