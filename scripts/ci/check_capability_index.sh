#!/usr/bin/env bash
# Capability-index freshness guard (pathway Move 1; report mode during rollout).
# The index is only trustworthy if regenerated after source changes — a stale
# index quietly re-enables "built-then-forgotten".
# Flip REPORT_ONLY=0 to enforce once the index lands in CI's generation step.
set -u
REPORT_ONLY="${REPORT_ONLY:-1}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
MD="$REPO/CAPABILITIES.md"

if [ ! -f "$MD" ]; then
  echo "[capability-index] MISSING: CAPABILITIES.md — run scripts/audits/capability_index.py"
  [ "$REPORT_ONLY" = "1" ] && exit 0 || exit 1
fi
newest_src=$(find "$REPO/src" "$REPO/scripts" -name "*.py" -newer "$MD" 2>/dev/null | head -5)
if [ -n "$newest_src" ]; then
  echo "[capability-index] STALE: source newer than CAPABILITIES.md:"
  echo "$newest_src"
  [ "$REPORT_ONLY" = "1" ] && exit 0 || exit 1
fi
echo "[capability-index] fresh"
exit 0
