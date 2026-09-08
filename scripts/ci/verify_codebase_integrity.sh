#!/usr/bin/env bash
# verify_codebase_integrity.sh — Fast fail-closed integrity gate.

set -euo pipefail

echo "🔍 [1/3] Checking Git index file count (Warning: >10k, Hard limit: 15,000)..."
INDEX_COUNT=$(git ls-files | wc -l)
echo "    Tracked files in index: ${INDEX_COUNT}"
if [ "${INDEX_COUNT}" -gt 15000 ]; then
    echo "❌ ERROR: Git index exceeds hard limit of 15,000 files (${INDEX_COUNT})!"
    exit 1
elif [ "${INDEX_COUNT}" -gt 10000 ]; then
    echo "    ⚠️  WARNING: Tracked files (${INDEX_COUNT}) exceed recommended 10k floor. Schedule cleanup of vendor dirs (e.g. cloud-vault-mcp, .pi)."
fi
echo "    ✓ Git index boundary check completed."

echo "🔍 [2/3] Checking Python AST syntax across staged/modified files..."
python3 -c '
import ast
import subprocess
import sys

res = subprocess.run(["git", "diff", "--name-only", "HEAD"], capture_output=True, text=True)
files = [f.strip() for f in res.stdout.splitlines() if f.strip().endswith(".py")]

for f in files:
    try:
        with open(f, "r", encoding="utf-8") as pyfile:
            ast.parse(pyfile.read(), filename=f)
        print(f"    ✓ AST valid: {f}")
    except Exception as e:
        print(f"    ❌ AST syntax error in {f}: {e}")
        sys.exit(1)
'
echo "    ✓ AST verification passed."

echo "🔍 [3/3] Running fast unit test verification (<5s)..."
pytest tests/physics/test_twistor_orch_or.py -q --no-header

echo "✅ All codebase integrity gates passed successfully!"
