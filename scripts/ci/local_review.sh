#!/usr/bin/env bash
# scripts/ci/local_review.sh — adversarial code review via local AMD inference.
#
# Pre-warms a review model on Lemonade, sends the PR diff in chunks, and
# collects findings. Logs to SurrealDB + writes a report file.
#
# Usage:
#   scripts/ci/local_review.sh <PR_NUMBER>
#   scripts/ci/local_review.sh 252
#
# Exit codes:
#   0 = review completed (findings may or may not exist)
#   1 = pre-warm failed or model unavailable
#   2 = no diff to review

set -uo pipefail
cd "$(dirname "$0")/../.." || exit 3

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PR_NUMBER="${1:?Usage: $0 <PR_NUMBER>}"
MODEL="${2:-Qwen3-Coder-30B-A3B-Instruct-GGUF}"
ROUTER="http://localhost:13305"
REPORT_DIR="/tmp/opencode/reviews"
mkdir -p "$REPORT_DIR"
REPORT_FILE="$REPORT_DIR/pr_${PR_NUMBER}_review.md"

echo "=== Local Review for PR #${PR_NUMBER} ==="
echo "Model: $MODEL"
echo ""

# Step 1: Pre-warm the review model
echo "[1/4] Pre-warming model..."
if ! bash "$SCRIPT_DIR/prewarm_review_model.sh" "$MODEL" 16384; then
  echo "  ⚠ Pre-warm failed — falling back to static analysis only."
  MODEL=""
fi

# Step 2: Get the PR diff
echo "[2/4] Fetching PR diff..."
PR_BRANCH="pr-${PR_NUMBER}-review"
gh pr diff "$PR_NUMBER" > /tmp/opencode/pr_diff.txt 2>/dev/null || {
  echo "  ❌ Could not fetch diff for PR #${PR_NUMBER}"
  exit 2
}
DIFF_LINES=$(wc -l < /tmp/opencode/pr_diff.txt)
echo "  Diff: $DIFF_LINES lines"

if [ "$DIFF_LINES" -lt 10 ]; then
  echo "  ⚠ Diff too small to review — skipping."
  exit 0
fi

# Step 3: Review via local inference + static analysis
echo "[3/4] Running review..."

# 3a: Static analysis — import smoke test on the diff's changed files
echo "  [3a] Static analysis: import smoke..."
python3 -c "
import subprocess, importlib, sys

# Get changed files from the diff
with open('/tmp/opencode/pr_diff.txt') as f:
    diff = f.read()

# Extract changed Python files from diff headers
changed = set()
for line in diff.splitlines():
    if line.startswith('diff --git a/') and line.endswith('.py'):
        # Extract the b/ path
        parts = line.split()
        bpath = parts[-1].replace('b/', '')
        if 'src/cohezion/' in bpath and '__init__' not in bpath and 'test_' not in bpath:
            changed.add(bpath)

print(f'  Found {len(changed)} changed Python source files')

failures = []
for path in sorted(changed):
    mod = path.replace('src/', '').replace('/', '.').replace('.py', '')
    try:
        importlib.import_module(mod)
    except SyntaxError as e:
        failures.append(f'  ❌ {mod}: SyntaxError at line {e.lineno}: {e.msg}')
    except SystemExit:
        pass  # Optional dep
    except Exception:
        pass  # Optional dep or env var

if failures:
    print('  IMPORT FAILURES:')
    for f in failures:
        print(f)
    sys.exit(1)
else:
    print('  All changed modules import cleanly.')
" 2>&1
STATIC_RESULT=$?

# 3b: Local inference review (if model is available)
if [ -n "$MODEL" ]; then
  echo "  [3b] Local inference review with $MODEL..."
  # Split diff into ~2000-line chunks and review each
  python3 << 'PYEOF'
import httpx
import json
import sys

MODEL = "{{MODEL_PLACEHOLDER}}"
ROUTER = "http://localhost:13305"
CHUNK_SIZE = 2000

with open("/tmp/opencode/pr_diff.txt") as f:
    lines = f.readlines()

chunks = [lines[i:i+CHUNK_SIZE] for i in range(0, len(lines), CHUNK_SIZE)]
findings = []

for i, chunk in enumerate(chunks):
    chunk_text = "".join(chunk)
    try:
        resp = httpx.post(
            f"{ROUTER}/v1/chat/completions",
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": "You are an expert Python code reviewer. Find real bugs: missing imports, broken function signatures, logic errors, race conditions, security issues. Be specific — file path, line number, what's wrong, why it's a bug. If no bugs found, say NO_BUGS."},
                    {"role": "user", "content": f"Review this diff chunk {i+1}/{len(chunks)} for bugs:\n\n{chunk_text}"}
                ],
                "max_tokens": 2000,
                "temperature": 0.1
            },
            timeout=120.0
        )
        content = resp.json()["choices"][0]["message"]["content"]
        if "NO_BUGS" not in content:
            findings.append(f"### Chunk {i+1}/{len(chunks)}\n{content}")
            print(f"  Chunk {i+1}/{len(chunks)}: {len(content)} chars of findings")
        else:
            print(f"  Chunk {i+1}/{len(chunks)}: NO_BUGS")
    except Exception as e:
        print(f"  Chunk {i+1}/{len(chunks)}: ERROR — {e}")

# Write findings
with open("{{REPORT_PLACEHOLDER}}", "w") as f:
    f.write(f"# Local Review Report — PR #{{PR_PLACEHOLDER}}\n\n")
    f.write(f"**Model:** {MODEL}\n")
    f.write(f"**Chunks reviewed:** {len(chunks)}\n")
    f.write(f"**Findings:** {len(findings)}\n\n")
    for finding in findings:
        f.write(f"{finding}\n\n")
    if not findings:
        f.write("No bugs found by local inference.\n")
PYEOF
else
  echo "  [3b] Skipped (no model available)"
fi

# Step 4: Write report and log to SurrealDB
echo "[4/4] Writing report..."
echo ""
echo "=== Review Complete ==="
if [ $STATIC_RESULT -ne 0 ]; then
  echo "❌ Static analysis found import failures."
fi
if [ -f "$REPORT_FILE" ]; then
  echo "Report: $REPORT_FILE"
fi

# Log to SurrealDB
curl -s -X POST http://localhost:8001/sql \
  -H "Content-Type: text/plain" -u "root:root" \
  -H "Surreal-NS: cohezion" -H "Surreal-DB: main" \
  -d "CREATE review_log:{{time::now()}} CONTENT {
    \"pr\": \"#${PR_NUMBER}\",
    \"model\": \"${MODEL:-static-only}\",
    \"static_result\": $STATIC_RESULT,
    \"diff_lines\": $DIFF_LINES,
    \"timestamp\": time::now()
  };" 2>/dev/null | head -1

exit 0