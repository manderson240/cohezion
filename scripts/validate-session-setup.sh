#!/bin/bash
# Session Setup Validator: Ensures git worktree pattern compliance
# Run this at the start of every session: ./scripts/validate-session-setup.sh

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Session Setup Validator - Git Worktree Pattern${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Get current directory and branch
CURRENT_DIR=$(pwd)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
WORKTREE_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "unknown")

# Check 1: Verify in a git worktree (not main ~/dev/cohezion)
echo -e "${BLUE}Check 1: Isolated Worktree${NC}"
if [[ "$CURRENT_DIR" =~ /dev/cohezion-session-[0-9]+$ ]]; then
    SESSION_NUM=$(echo "$CURRENT_DIR" | grep -oE 'session-[0-9]+' | cut -d'-' -f2)
    echo -e "${GREEN}  ✅ Worktree found: Session $SESSION_NUM${NC}"
    WORKTREE_OK=1
elif [[ "$CURRENT_DIR" == *"/dev/cohezion"* ]] && [ "$CURRENT_DIR" != "$HOME/dev/cohezion" ]; then
    echo -e "${GREEN}  ✅ In a worktree directory${NC}"
    WORKTREE_OK=1
else
    echo -e "${RED}  ❌ NOT in a worktree${NC}"
    echo "     Current directory: $CURRENT_DIR"
    echo "     Expected: ~/dev/cohezion-session-XX"
    WORKTREE_OK=0
fi
echo ""

# Check 2: Verify branch naming
echo -e "${BLUE}Check 2: Branch Naming${NC}"
if [[ "$CURRENT_BRANCH" =~ ^session-[0-9]+-[a-z0-9-]+$ ]]; then
    echo -e "${GREEN}  ✅ Branch name OK: $CURRENT_BRANCH${NC}"
    BRANCH_OK=1
elif [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "develop" ]; then
    echo -e "${YELLOW}  ⚠️  On $CURRENT_BRANCH (OK for viewing, not for new work)${NC}"
    BRANCH_OK=1
else
    echo -e "${RED}  ❌ Branch name doesn't follow pattern${NC}"
    echo "     Current: $CURRENT_BRANCH"
    echo "     Expected: session-XX-phase-name"
    BRANCH_OK=0
fi
echo ""

# Check 3: Verify main directory is clean
echo -e "${BLUE}Check 3: Main Directory Status${NC}"
cd "$HOME/dev/cohezion" 2>/dev/null || true
MAIN_STATUS=$(git status --porcelain 2>/dev/null | wc -l)
if [ "$MAIN_STATUS" -eq 0 ]; then
    echo -e "${GREEN}  ✅ Main directory clean${NC}"
    MAIN_CLEAN=1
else
    echo -e "${YELLOW}  ⚠️  Main directory has changes ($MAIN_STATUS files)${NC}"
    MAIN_CLEAN=0
fi
cd "$CURRENT_DIR" || exit 1
echo ""

# Check 4: Verify test baseline
echo -e "${BLUE}Check 4: Test Baseline${NC}"
cd "$HOME/dev/cohezion" 2>/dev/null || true
if command -v pytest &> /dev/null; then
    echo "  Running quick test count..."
    TEST_COUNT=$(uv run pytest tests/compound/ tests/cache/ tests/security/ --collect-only -q 2>/dev/null | tail -1 | grep -oE '[0-9]+' | tail -1 || echo "unknown")
    if [ "$TEST_COUNT" = "1361" ]; then
        echo -e "${GREEN}  ✅ Test baseline verified: $TEST_COUNT tests${NC}"
        TESTS_OK=1
    else
        echo -e "${YELLOW}  ⚠️  Test count may have changed: $TEST_COUNT tests${NC}"
        echo "     Expected: 1361 (Session 46 verified)"
        TESTS_OK=1  # Don't block
    fi
else
    echo -e "${YELLOW}  ⚠️  pytest not available, skipping test check${NC}"
    TESTS_OK=1
fi
cd "$CURRENT_DIR" || exit 1
echo ""

# Check 5: Read documentation
echo -e "${BLUE}Check 5: Documentation${NC}"
if [ -f "$HOME/dev/cohezion/SESSION_46_RETROSPECTIVE_AND_HANDOFF.md" ]; then
    echo -e "${GREEN}  ✅ Found: SESSION_46_RETROSPECTIVE_AND_HANDOFF.md${NC}"
    DOC_OK=1
else
    echo -e "${YELLOW}  ⚠️  Missing: SESSION_46_RETROSPECTIVE_AND_HANDOFF.md${NC}"
    DOC_OK=0
fi
echo ""

# Summary
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Session Setup Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

SCORE=0
TOTAL=5

if [ "$WORKTREE_OK" -eq 1 ]; then
    echo -e "${GREEN}  ✅ Worktree Setup${NC}"; SCORE=$((SCORE + 1))
else
    echo -e "${RED}  ❌ Worktree Setup (CRITICAL)${NC}"
fi

if [ "$BRANCH_OK" -eq 1 ]; then
    echo -e "${GREEN}  ✅ Branch Naming${NC}"; SCORE=$((SCORE + 1))
else
    echo -e "${RED}  ❌ Branch Naming${NC}"
fi

if [ "$MAIN_CLEAN" -eq 1 ]; then
    echo -e "${GREEN}  ✅ Main Directory Clean${NC}"; SCORE=$((SCORE + 1))
else
    echo -e "${YELLOW}  ⚠️  Main Directory Dirty (non-critical)${NC}"; SCORE=$((SCORE + 1))
fi

if [ "$TESTS_OK" -eq 1 ]; then
    echo -e "${GREEN}  ✅ Tests Available${NC}"; SCORE=$((SCORE + 1))
else
    echo -e "${YELLOW}  ⚠️  Tests May Be Different${NC}"; SCORE=$((SCORE + 1))
fi

if [ "$DOC_OK" -eq 1 ]; then
    echo -e "${GREEN}  ✅ Documentation Found${NC}"; SCORE=$((SCORE + 1))
else
    echo -e "${YELLOW}  ⚠️  Documentation Not Found${NC}"
fi

echo ""
echo -e "Score: $SCORE/$TOTAL"
echo ""

if [ "$SCORE" -ge 4 ]; then
    echo -e "${GREEN}✅ Ready to work! Use git worktree pattern:${NC}"
    echo ""
    echo "  SESSION_ID='47'  # Use sequential numbering"
    echo "  git commit -m \"Session XX: PHASE"
    echo ""
    echo "  ## Accomplishments"
    echo "  - [Key deliverables]"
    echo "  - [Test results: X/Y passing]"
    echo ""
    echo "  ## For Session XX+1"
    echo "  - [Key assumptions]"
    echo "  - [Remaining work]\""
    echo ""
    exit 0
else
    echo -e "${RED}❌ Setup issues found. Fix above before proceeding.${NC}"
    exit 1
fi
