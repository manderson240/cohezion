#!/usr/bin/env bash
# Pre-commit hook: Prevent session artifact accumulation at repo root.
#
# Blocks commits that stage NEW files at the repo root unless they match
# the allowlist of known config/project files. This catches the accumulation
# pattern where AI sessions drop SESSION_*.md, PHASE_*.md, DEPLOYMENT_GUIDE_*.md,
# etc. into the root — patterns that .gitignore alone cannot fully prevent
# (gitignore only blocks numbered prefixes like SESSION_[0-9]*).
#
# Override: If you legitimately need a new root file, add it to ROOT_ALLOWLIST below.

set -euo pipefail

# --- Configuration ---

# Maximum root .md files allowed (currently 5 essential: CLAUDE, README,
# CONTRIBUTING, CREDITS, CONTRIBUTOR_LICENSE_AGREEMENT)
MAX_ROOT_MD=7

# Known root files that are allowed. This is a regex alternation.
# Dotfiles (.*) are always allowed and don't need to be listed.
ROOT_ALLOWLIST='^\./('
ROOT_ALLOWLIST+='CLAUDE\.md|README\.md|CONTRIBUTING\.md|CREDITS\.md|CONTRIBUTOR_LICENSE_AGREEMENT\.md'  # essential docs
ROOT_ALLOWLIST+='|pyproject\.toml|Makefile|uv\.lock|pytest\.ini'                                       # build/project
ROOT_ALLOWLIST+='|docker-compose\.yml|docker-compose\.notebooks\.yml|cloudbuild\.yaml'                  # deploy
ROOT_ALLOWLIST+='|mcp_servers\.json|model_registry\.json'                                              # runtime config
ROOT_ALLOWLIST+='|main\.py|check_bbq_status\.py|scan_todos\.py|overnight_driver\.py'                   # scripts with code refs
ROOT_ALLOWLIST+='|CHANGELOG\.md|LICENSE|LICENSE\.md'                                                   # standard project files
ROOT_ALLOWLIST+=')$'

# --- Checks ---

ERRORS=0

# 1. Check root .md file count (staged + existing)
ROOT_MD_COUNT=$(find . -maxdepth 1 -name '*.md' -type f 2>/dev/null | wc -l)
if [ "$ROOT_MD_COUNT" -gt "$MAX_ROOT_MD" ]; then
    echo "❌ ROOT HYGIENE: $ROOT_MD_COUNT markdown files at repo root (max: $MAX_ROOT_MD)"
    echo "   Essential files: CLAUDE.md, README.md, CONTRIBUTING.md, CREDITS.md, CONTRIBUTOR_LICENSE_AGREEMENT.md"
    echo "   Extra files found:"
    find . -maxdepth 1 -name '*.md' -type f | sort | while read -r f; do
        base=$(basename "$f")
        case "$base" in
            CLAUDE.md|README.md|CONTRIBUTING.md|CREDITS.md|CONTRIBUTOR_LICENSE_AGREEMENT.md) ;;
            *) echo "     - $base" ;;
        esac
    done
    echo "   Fix: Move non-essential .md files to docs/ or docs/archive/"
    ERRORS=$((ERRORS + 1))
fi

# 2. Check if any NEW files at root are being staged (additions only)
while IFS= read -r file; do
    # Only check files at repo root (no directory separator after ./)
    dir=$(dirname "$file")
    if [ "$dir" != "." ]; then
        continue
    fi

    # Skip dotfiles (config files like .gitignore, .env, etc.)
    base=$(basename "$file")
    if [[ "$base" == .* ]]; then
        continue
    fi

    # Check against allowlist
    if ! echo "./$base" | grep -qE "$ROOT_ALLOWLIST"; then
        echo "❌ ROOT HYGIENE: New file at repo root is not in allowlist: $base"
        echo "   Session artifacts belong in docs/archive/ or a subdirectory."
        echo "   If this file is legitimate, add it to ROOT_ALLOWLIST in scripts/hooks/check-root-hygiene.sh"
        ERRORS=$((ERRORS + 1))
    fi
done < <(git diff --cached --name-only --diff-filter=A 2>/dev/null)

if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo "❌ Root hygiene check failed ($ERRORS issue(s))"
    echo "   This hook prevents session artifact accumulation at the repo root."
    echo "   See: docs/plans/2026-02-14-repository-cleanup.md (Adversarial Retrospective)"
    exit 1
fi

echo "✓ Root hygiene OK ($ROOT_MD_COUNT markdown files at root)"
exit 0
