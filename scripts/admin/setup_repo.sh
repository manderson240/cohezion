#!/usr/bin/env bash
# ONE-TIME ADMIN SETUP — Run locally with: gh auth login (admin access required).
# Do NOT add to CI workflows — requires admin-level GitHub token.
#
# Usage: bash scripts/admin/setup_repo.sh
#
# Configures manderson240/cohezion repository for autonomous merge flow:
#   - Squash-merge-only (disables merge commit and rebase)
#   - Auto-merge enabled
#   - Delete-branch-on-merge enabled
#   - Branch protection ruleset on main

set -euo pipefail

REPO="manderson240/cohezion"
RULESET_NAME="main-protection"

# Guard: refuse to run in CI environments
if [[ -n "${CI:-}" ]]; then
  echo "ERROR: This script requires admin access and must not run in CI." >&2
  exit 1
fi

echo "=== Cohezion Repo Setup ==="
echo "Repository: $REPO"
echo ""

# ── Part 1: Repository Settings ───────────────────────────────────────────────

echo "── Configuring merge settings..."
gh repo edit "$REPO" \
  --enable-squash-merge \
  --enable-merge-commit=false \
  --enable-rebase-merge=false \
  --delete-branch-on-merge=true

echo "── Enabling auto-merge..."
gh api "repos/$REPO" \
  --method PATCH \
  --field allow_auto_merge=true \
  --silent

echo "✓ Repository settings applied"

# ── Part 2: GitHub Ruleset on main ────────────────────────────────────────────

echo ""
echo "── Checking for existing ruleset '$RULESET_NAME'..."

EXISTING_ID=$(gh api "repos/$REPO/rulesets" 2>/dev/null \
  | python3 -c "
import json, sys
rulesets = json.load(sys.stdin)
for r in rulesets:
    if r.get('name') == '$RULESET_NAME':
        print(r['id'])
        break
" 2>/dev/null || echo "")

if [[ -n "$EXISTING_ID" ]]; then
  echo "  Ruleset '$RULESET_NAME' already exists (id=$EXISTING_ID) — skipping creation"
else
  echo "── Creating ruleset '$RULESET_NAME'..."

  RULESET_JSON=$(cat <<EOF
{
  "name": "$RULESET_NAME",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "bypass_actors": [
    {
      "actor_id": 5,
      "actor_type": "RepositoryRole",
      "bypass_mode": "always"
    }
  ],
  "rules": [
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "required_status_checks": [
          {"context": "lint"},
          {"context": "validate"},
          {"context": "test"},
          {"context": "ci-status"},
          {"context": "commit-lint"}
        ],
        "strict_required_status_checks_policy": false
      }
    },
    {
      "type": "non_fast_forward"
    },
    {
      "type": "deletion"
    }
  ]
}
EOF
)

  gh api "repos/$REPO/rulesets" \
    --method POST \
    --input - <<< "$RULESET_JSON"

  echo "✓ Ruleset '$RULESET_NAME' created"
fi

# ── Part 3: Verification ───────────────────────────────────────────────────────

echo ""
echo "=== Verification Summary ==="
echo ""
echo "── Merge settings:"
gh repo view "$REPO" \
  --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,deleteBranchOnMerge \
  --jq '
    "  squash-only:         " + (if .squashMergeAllowed and (.mergeCommitAllowed | not) and (.rebaseMergeAllowed | not) then "✓" else "✗" end),
    "  delete-branch:       " + (if .deleteBranchOnMerge then "✓" else "✗" end)
  '

echo "  auto-merge:          $(gh api "repos/$REPO" --jq 'if .allow_auto_merge then "✓" else "✗" end')"

echo ""
echo "── Active rulesets:"
gh api "repos/$REPO/rulesets" \
  --jq '.[] | "  " + .name + " [" + .enforcement + "]"' 2>/dev/null || echo "  (none)"

echo ""
echo "=== Setup complete ==="
