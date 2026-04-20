#!/bin/bash
# Pre-commit hook: Prevent large artifacts from being committed
# This enforces artifact governance and prevents repository bloat
# Reference: CLAUDE.md "Data Storage Architecture for Simulations"

set -euo pipefail

# Configuration
MAX_FILE_SIZE=$((50 * 1024 * 1024))  # 50 MB threshold
ERRORS=0

echo "🔍 Checking for large artifact files (>50MB)..."

# Check staged files
while IFS= read -r file; do
  if [ ! -f "$file" ]; then
    continue
  fi

  size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
  size_mb=$((size / 1024 / 1024))

  if [ "$size" -gt "$MAX_FILE_SIZE" ]; then
    echo "❌ ERROR: Large artifact detected: $file ($size_mb MB)"
    echo "   This file exceeds the 50 MB threshold and cannot be committed."
    echo "   "
    echo "   For large artifacts, use artifact tiering:"
    echo "   - Tier 1 (Git): Metadata only, configs, checksums"
    echo "   - Tier 2 (SurrealDB): Index via JourneyTracker.record_artifact()"
    echo "   - Tier 3 (External): s3, GCS, or local archive"
    echo "   "
    echo "   To register this artifact: uv run python -c '"
    echo '     from cohezion.compound.journey_tracker import JourneyTracker
    echo '     JourneyTracker.record_artifact('
    echo '       session_id="current",'
    echo '       artifact_type="checkpoint",'
    echo '       path="'"$file"'",'
    echo '       tier="external",'
    echo '       lifetime_days=30'
    echo '     )'
    echo "   '"
    ERRORS=$((ERRORS + 1))
  fi
done < <(git diff --cached --name-only)

if [ "$ERRORS" -gt 0 ]; then
  echo ""
  echo "❌ Commit blocked: $ERRORS large file(s) detected"
  echo "   Fix: Move files to appropriate tier and try again"
  exit 1
fi

echo "✓ All staged files are within size limits"
exit 0
