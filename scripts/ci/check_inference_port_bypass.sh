#!/usr/bin/env bash
# CB/N4 guard: flag direct references to the dead per-port Lemonade servers
# (11434 Ollama, 13306 NPU, 13307/13308 iGPU, 13309 CPU) outside the single
# :13305 OmniRouter path. See ~/.claude/rules/harness.md N4.
#
# Recreated 2026-07-06: harness.md referenced this script and a `clasp_tier.py`
# allow-list entry, but neither existed anywhere in the repo — this is a fresh,
# honest rebuild using only allow-list entries that are actually present today
# (direct_tier.py, health.py, the N2-retained cpu_port line in
# triune_orchestrator.py). Report mode only — the violation count is nowhere
# near zero, so fail mode would be dishonest; migration status unverified.
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

PATTERN='\b(11434|1330[6-9])\b'

violations=0
while IFS=: read -r file line content; do
  # Inline per-line override
  if [[ "$content" == *"# allow-direct-port:"* ]]; then
    continue
  fi
  # Path-based allow-list: confirmed-real exception files/dirs
  case "$file" in
    *dead/*|*benchmark*|*demo*|*archive*) continue ;;
    src/cohezion/inference/direct_tier.py) continue ;;
    src/cohezion/inference/health.py) continue ;;
  esac
  # File-specific single-line allow: N2-retained cpu_port default
  if [[ "$file" == "src/cohezion/inference/triune_orchestrator.py" ]] && [[ "$content" == *"cpu_port: int = 13309"* ]]; then
    continue
  fi
  violations=$((violations + 1))
  echo "$file:$line:$content"
done < <(grep -rnE "$PATTERN" src/cohezion/ --include="*.py" || true)

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
