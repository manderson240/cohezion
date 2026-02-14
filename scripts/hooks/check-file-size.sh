#!/bin/bash
# Pre-commit hook: Block large files (>1MB) from being committed
# Part of repository health governance (Session 55, Task #7)

set -e

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

MAX_SIZE=1048576  # 1MB in bytes
BLOCKED=0

echo -e "${YELLOW}Checking file sizes...${NC}"

# Check all staged files
for file in $(git diff --cached --name-only --diff-filter=ACM); do
    if [ -f "$file" ]; then
        # Get file size (Linux stat command)
        size=$(stat -c%s "$file" 2>/dev/null || echo 0)

        if [ "$size" -gt "$MAX_SIZE" ]; then
            # Format size in human-readable format
            size_human=$(numfmt --to=iec-i --suffix=B "$size" 2>/dev/null || echo "${size} bytes")

            echo -e "${RED}❌ ERROR: File exceeds 1MB: $file ($size_human)${NC}"
            echo -e "${YELLOW}Recommendation:${NC}"
            echo "  - Add to .gitignore if ephemeral data (logs, cache, temp files)"
            echo "  - Use git-lfs if needed for version control (checkpoints, models)"
            echo "  - Use external storage if artifact (SurrealDB, S3, vault)"
            echo ""
            BLOCKED=1
        fi
    fi
done

if [ "$BLOCKED" -eq 1 ]; then
    echo ""
    echo -e "${RED}❌ Commit blocked due to large files${NC}"
    echo -e "${YELLOW}To bypass (NOT RECOMMENDED): git commit --no-verify${NC}"
    echo ""
    echo "For more info, see: /tmp/repository_health_governance.md"
    exit 1
fi

echo -e "${GREEN}✅ File size check passed${NC}"
exit 0
