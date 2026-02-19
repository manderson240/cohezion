#!/usr/bin/env bash
# Fix 3 review findings on spec/autonomous-repo-management PR branch
# Run from repo root: bash fix-pr-findings.sh
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== Checking out PR branch ==="
# Fetch all remote branches (worktree cleanup may have deleted local ref)
git fetch origin
# Create local branch tracking the remote
git checkout -b spec/autonomous-repo-management origin/spec/autonomous-repo-management 2>/dev/null \
  || git checkout spec/autonomous-repo-management

echo ""
echo "=== Fix 1: ci-status needs list (remove advisory jobs) ==="
sed -i 's/needs: \[lint, validate, test, compound, typecheck\]/needs: [lint, validate, test]/' .github/workflows/ci.yml
echo "Done"

echo ""
echo "=== Fix 2: cloud-vault-mcp uses bare pip/pytest → uv ==="
# Only target lines inside the cloud-vault-mcp section (after the cd cloud-vault-mcp)
sed -i '/cloud-vault-mcp/,$ {
  s/run: pip install -e \./run: uv pip install -e ./
  s/run: pytest tests\/ -q/run: uv run pytest tests\/ -q/
}' .github/workflows/ci.yml
echo "Done"

echo ""
echo "=== Fix 3: setup_repo.sh — pass RULESET_NAME via sys.argv ==="
# Replace the Python snippet to use sys.argv instead of shell interpolation
cat > /tmp/setup_fix.py << 'PYEOF'
import sys

filepath = sys.argv[1]
with open(filepath) as f:
    content = f.read()

old = """EXISTING_ID=$(gh api "repos/$REPO/rulesets" 2>/dev/null \\
  | python3 -c "
import json, sys
rulesets = json.load(sys.stdin)
for r in rulesets:
    if r.get('name') == '$RULESET_NAME':
        print(r['id'])
        break
" 2>/dev/null || echo "")"""

new = """EXISTING_ID=$(gh api "repos/$REPO/rulesets" 2>/dev/null \\
  | python3 -c "
import json, sys
name = sys.argv[1]
rulesets = json.load(sys.stdin)
for r in rulesets:
    if r.get('name') == name:
        print(r['id'])
        break
" "$RULESET_NAME" 2>/dev/null || echo "")"""

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print("Replaced shell interpolation with sys.argv")
else:
    print("WARNING: Could not find exact match. Manual edit needed.")
    sys.exit(1)
PYEOF
python3 /tmp/setup_fix.py scripts/admin/setup_repo.sh
echo "Done"

echo ""
echo "=== Verifying changes ==="
git diff --stat
echo ""
git diff

echo ""
echo "=== Committing and pushing ==="
git add .github/workflows/ci.yml scripts/admin/setup_repo.sh
git commit -m "$(cat <<'EOF'
fix(spec): address review findings in ci.yml and setup_repo.sh

- Remove advisory jobs (compound, typecheck) from ci-status needs list
- Use uv pip install/uv run pytest for cloud-vault-mcp CI steps
- Pass RULESET_NAME as sys.argv instead of shell interpolation in heredoc
EOF
)"
git push

echo ""
echo "=== Done! Switching back to original branch ==="
git checkout spec/routes-consolidation
rm -f fix-pr-findings.sh
echo "Fixes pushed to PR #11"
