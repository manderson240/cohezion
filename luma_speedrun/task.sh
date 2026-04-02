#!/usr/bin/env bash
# Luma Speedrun - Task Management Script

set -e

LUMA_DIR="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
WORKTREE=".worktrees/luma-breakthrough-sprint"
BRANCH="luma-breakthrough-sprint"

cd /home/mike-anderson/dev/cohezion

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    echo "Luma Speedrun Task Manager"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  status          Show current project status"
    echo "  worktree        Ensure worktree is setup"
    echo "  fix-coherence   Fix toFixed errors across all TS files"
    echo "  submit-gemm     Submit GEMM kernel"
    echo "  submit-mla      Submit MLA kernel"
    echo "  submit-moe      Submit MoE kernel"
    echo "  rl-run [k]      Run RL optimizer for kernel (gemm|mla|moe)"
    echo "  commit [msg]    Commit changes to worktree"
    echo "  sync            Sync worktree with main"
    echo ""
}

show_status() {
    echo -e "${BLUE}=== Luma Speedrun Status ===${NC}"
    echo ""
    
    # Branch status
    echo -e "${YELLOW}Git Status:${NC}"
    git -C "$LUMA_DIR" status --short
    echo ""
    
    # Recent commits
    echo -e "${YELLOW}Recent commits:${NC}"
    git -C "$LUMA_DIR" log --oneline -5
    echo ""
    
    # Current best scores
    echo -e "${YELLOW}Current Best Scores:${NC}"
    echo "  GEMM: 22.8µs (target: 4.3µs)"
    echo "  MLA:  69.7µs (target: 33.0µs)"
    echo "  MoE:  154.2µs (target: 109.8µs)"
    echo ""
    
    # Check for coherence errors
    echo -e "${YELLOW}Coherence Error Check:${NC}"
    ERRORS=$(grep -rn "coherence\.toFixed\|entropy\.toFixed" "$LUMA_DIR/apps" --include="*.tsx" 2>/dev/null | wc -l)
    if [ "$ERRORS" -gt 0 ]; then
        echo -e "  ${RED}⚠ Found $ERRORS files with potential coherence errors${NC}"
        grep -rln "coherence\.toFixed\|entropy\.toFixed" "$LUMA_DIR/apps" --include="*.tsx" 2>/dev/null | head -5 | sed 's/^/    /'
    else
        echo -e "  ${GREEN}✓ No coherence errors found${NC}"
    fi
    echo ""
    
    # Check worktree
    echo -e "${YELLOW}Worktree Status:${NC}"
    if [ -d "$LUMA_DIR" ]; then
        echo -e "  ${GREEN}✓ Worktree exists: $WORKTREE${NC}"
    else
        echo -e "  ${RED}✗ Worktree missing${NC}"
    fi
}

ensure_worktree() {
    if [ ! -d "$LUMA_DIR" ]; then
        echo -e "${YELLOW}Creating worktree from branch $BRANCH...${NC}"
        git worktree add "$WORKTREE" "$BRANCH"
    else
        echo -e "${GREEN}Worktree already exists: $WORKTREE${NC}"
    fi
}

fix_coherence() {
    echo -e "${YELLOW}Fixing coherence toFixed errors...${NC}"
    
    # Fix LandingPage.tsx
    sed -i 's/ouroboros\.coherence\.toFixed/(ouroboros.coherence ?? 0).toFixed/g' "$LUMA_DIR/apps/webapp/src/components/LandingPage.tsx"
    sed -i 's/ouroboros\.entropy\.toFixed/(ouroboros.entropy ?? 0).toFixed/g' "$LUMA_DIR/apps/webapp/src/components/LandingPage.tsx"
    
    # Fix ManifoldCanvas.tsx
    sed -i 's/latestPoint\.coherence\.toFixed/latestPoint.coherence?.toFixed/g' "$LUMA_DIR/apps/webapp/src/components/Universe/ManifoldCanvas.tsx"
    sed -i 's/v => v\.toFixed/v => (v ?? 0).toFixed/g' "$LUMA_DIR/apps/webapp/src/components/Universe/ManifoldCanvas.tsx"
    
    # Fix HologramField.tsx
    sed -i 's/randomNode\.coherence\?\.toFixed/(randomNode.coherence ?? 0).toFixed/g' "$LUMA_DIR/apps/webapp/src/components/Universe/HologramField.tsx"
    
    # Fix morphospace-loom
    sed -i 's/{value\.toFixed/(value ?? 0).toFixed/g' "$LUMA_DIR/apps/morphospace-loom/src/App.tsx"
    sed -i 's/{d1\.toFixed/(d1 ?? 0).toFixed/g' "$LUMA_DIR/apps/morphospace-loom/src/App.tsx"
    sed -i 's/{d12\.toFixed/(d12 ?? 0).toFixed/g' "$LUMA_DIR/apps/morphospace-loom/src/App.tsx"
    
    echo -e "${GREEN}✓ Fixed coherence errors${NC}"
    
    # Show remaining issues
    REMAINING=$(grep -rn "coherence\.toFixed\|entropy\.toFixed" "$LUMA_DIR/apps" --include="*.tsx" 2>/dev/null | grep -v "??" | wc -l)
    if [ "$REMAINING" -gt 0 ]; then
        echo -e "${YELLOW}⚠ $REMAINING potential issues remain (check manually)${NC}"
    fi
}

run_rl_optimizer() {
    KERNEL="${1:-gemm}"
    CYCLES="${2:-10}"
    
    echo -e "${BLUE}Running RL optimizer for $KERNEL kernel...${NC}"
    echo "  Cycles: $CYCLES"
    echo "  Target: GEMM <5µs, MLA <35µs, MoE <110µs"
    echo ""
    
    cd "$LUMA_DIR"
    python -m luma_speedrun.autoresearch.driver \
        --kernel "$KERNEL" \
        --max-cycles "$CYCLES" \
        2>&1 | tee "logs/rl_${KERNEL}_$(date +%Y%m%d_%H%M%S).log"
}

commit_changes() {
    MSG="${1:-update: luma speedrun progress}"
    
    cd "$LUMA_DIR"
    git add -A
    git commit -m "$MSG" || echo "Nothing to commit"
    
    echo -e "${GREEN}✓ Committed: $MSG${NC}"
}

sync_worktree() {
    echo -e "${YELLOW}Syncing worktree with main...${NC}"
    
    # Fetch latest
    git fetch origin
    
    # Rebase worktree
    cd "$LUMA_DIR"
    git rebase origin/main || {
        echo -e "${RED}Rebase failed, manual intervention needed${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✓ Worktree synced${NC}"
}

# Main command dispatch
case "${1:-status}" in
    status)
        show_status
        ;;
    worktree)
        ensure_worktree
        ;;
    fix-coherence)
        fix_coherence
        ;;
    rl-run)
        run_rl_optimizer "${2:-gemm}" "${3:-10}"
        ;;
    submit-gemm)
        echo "Submitting GEMM..."
        cd "$LUMA_DIR"
        popcorn-cli submit luma_speedrun/amd-mxfp4-mm/submission.py --mode test --gpu MI355X --leaderboard amd-fp8-gemm
        ;;
    submit-mla)
        echo "Submitting MLA..."
        cd "$LUMA_DIR"
        popcorn-cli submit luma_speedrun/amd-mixed-mla/submission.py --mode test --gpu MI355X --leaderboard amd-mla
        ;;
    submit-moe)
        echo "Submitting MoE..."
        cd "$LUMA_DIR"
        popcorn-cli submit luma_speedrun/amd-moe-mxfp4/submission.py --mode test --gpu MI355X --leaderboard amd-moe-mxfp4
        ;;
    commit)
        commit_changes "${2:-update: luma speedrun progress}"
        ;;
    sync)
        sync_worktree
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        usage
        exit 1
        ;;
esac