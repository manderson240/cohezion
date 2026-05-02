#!/bin/bash
# Weekly repository maintenance script
# Session 55, Task #7: Repository health governance
# Layer 3: Remediation - automated cleanup and optimization
#
# Run via cron: 0 2 * * 0 (Sunday 2am)
# Or manually: ./scripts/maintenance/weekly_repo_maintenance.sh

set -e

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COHEZION_HOME="${COHEZION_HOME:-/home/mike-anderson/dev/cohezion}"
LOG_FILE="${LOG_FILE:-/var/log/cohezion-repo-maintenance.log}"
DRY_RUN="${DRY_RUN:-0}"

echo -e "${BLUE}=== COHEZION Repository Maintenance ===${NC}"
echo "Started at: $(date)"
echo "Repository: $COHEZION_HOME"
echo ""

cd "$COHEZION_HOME" || exit 1

# Dry run mode
if [ "$DRY_RUN" -eq 1 ]; then
    echo -e "${YELLOW}⚠️  DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

# Check 1: Repository size before maintenance
echo -e "${BLUE}[1/6] Checking repository size (before)...${NC}"
SIZE_BEFORE=$(du -sh .git | cut -f1)
SIZE_BYTES_BEFORE=$(du -sb .git | cut -f1)
echo "  Current size: $SIZE_BEFORE"
echo ""

# Check 2: Count objects
echo -e "${BLUE}[2/6] Counting git objects...${NC}"
git count-objects -vH
echo ""

# Check 3: Clean reflog (keep 30 days)
echo -e "${BLUE}[3/6] Cleaning reflog (keeping 30 days)...${NC}"
if [ "$DRY_RUN" -eq 0 ]; then
    git reflog expire --expire=30.days.ago --all
    git reflog expire --expire-unreachable=7.days.ago --all
    echo -e "${GREEN}  ✅ Reflog cleaned${NC}"
else
    echo -e "${YELLOW}  (Skipped - dry run)${NC}"
fi
echo ""

# Check 4: Prune remote-tracking branches
echo -e "${BLUE}[4/6] Pruning remote branches...${NC}"
if [ "$DRY_RUN" -eq 0 ]; then
    git remote prune origin
    echo -e "${GREEN}  ✅ Remote branches pruned${NC}"
else
    echo -e "${YELLOW}  (Skipped - dry run)${NC}"
fi
echo ""

# Check 5: Aggressive garbage collection
echo -e "${BLUE}[5/6] Running git gc --aggressive...${NC}"
echo "  This may take several minutes..."
if [ "$DRY_RUN" -eq 0 ]; then
    # Run with nice to avoid blocking other processes
    nice -n 10 git gc --aggressive --prune=now
    echo -e "${GREEN}  ✅ Garbage collection complete${NC}"
else
    echo -e "${YELLOW}  (Skipped - dry run)${NC}"
fi
echo ""

# Check 6: Repository size after maintenance
echo -e "${BLUE}[6/6] Checking repository size (after)...${NC}"
SIZE_AFTER=$(du -sh .git | cut -f1)
SIZE_BYTES_AFTER=$(du -sb .git | cut -f1)
echo "  Size after: $SIZE_AFTER"

# Calculate savings
SAVED_BYTES=$((SIZE_BYTES_BEFORE - SIZE_BYTES_AFTER))
SAVED_MB=$((SAVED_BYTES / 1024 / 1024))

if [ "$SAVED_BYTES" -gt 0 ]; then
    echo -e "${GREEN}  ✅ Saved: ${SAVED_MB} MB${NC}"
elif [ "$SAVED_BYTES" -lt 0 ]; then
    INCREASED_MB=$((-SAVED_MB))
    echo -e "${YELLOW}  ⚠️  Size increased: ${INCREASED_MB} MB${NC}"
    echo "     (Normal after gc --aggressive due to pack rewriting)"
else
    echo "  No change"
fi
echo ""

# Report largest objects in history
echo -e "${BLUE}=== Top 10 Largest Objects in History ===${NC}"
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '$1 == "blob" && $3 > 1048576 {printf "%.2f MB: %s\n", $3/1048576, $4}' | \
  sort -rn | head -10

echo ""
echo -e "${GREEN}=== Maintenance Complete ===${NC}"
echo "Completed at: $(date)"
echo "Summary:"
echo "  - Before: $SIZE_BEFORE"
echo "  - After:  $SIZE_AFTER"
echo "  - Saved:  ${SAVED_MB} MB"
echo ""

# Warning if still large
SIZE_GB=$((SIZE_BYTES_AFTER / 1024 / 1024 / 1024))
if [ "$SIZE_GB" -gt 6 ]; then
    echo -e "${YELLOW}⚠️  WARNING: Repository size ($SIZE_GB GB) exceeds 6GB target${NC}"
    echo "   Review large files and consider git-lfs migration"
    echo "   See: /tmp/repository_health_governance.md"
fi

exit 0
