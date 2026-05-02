#!/usr/bin/env bash
set -euo pipefail
# Autoresearch: PR merge optimization
# Measures mergeability and CI status for polish/feature PRs

PR_COUNT=$(gh pr list --repo manderson240/cohezion --json number --jq 'length' 2>/dev/null || echo 0)
echo "METRIC pr_count=$PR_COUNT"

MERGED=$(gh pr list --repo manderson240/cohezion --state merged --json number --jq 'length' 2>/dev/null || echo 0)
echo "METRIC merged_count=$MERGED"

CONFLICTS=$(gh pr list --repo manderson240/cohezion --json mergeable --jq '[.[] | select(.mergeable == "CONFLICTING")] | length' 2>/dev/null || echo 0)
echo "METRIC conflicts=$CONFLICTS"

# Check latest CI on main
MAIN_CI=$(gh run list --repo manderson240/cohezion --branch main --workflow "CI Pipeline" --limit 1 --json conclusion --jq '.[0].conclusion // "none"' 2>/dev/null)
echo "METRIC main_ci_status=$MAIN_CI"
