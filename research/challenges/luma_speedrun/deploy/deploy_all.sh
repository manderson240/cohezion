#!/bin/bash
# DEPLOY ALL SCRIPT - Luma AMD Speedrun
# Tests all Tier 1 (breakthrough) and Tier 2 (best) kernels

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_FILE="deployment_$(date +%Y%m%d_%H%M%S).log"
RESULTS_FILE="results_$(date +%Y%m%d_%H%M%S).log"

echo "=================================="
echo "Luma AMD Speedrun - Deployment Run"
echo "Started: $(date)"
echo "Log: $LOG_FILE"
echo "Results: $RESULTS_FILE"
echo "=================================="

# Initialize results log
cat > "$RESULTS_FILE" << 'EOF'
# Luma AMD Speedrun - Deployment Results
# Generated: DATE_PLACEHOLDER

## Test Results

### Tier 1: Breakthrough Candidates

| Kernel | Test | Benchmark | Leaderboard | Notes |
|--------|------|-----------|-------------|-------|
| moe_breakthrough | ⬜ | ⬜ | ⬜ | |
| mla_breakthrough | ⬜ | ⬜ | ⬜ | |
| gemm_breakthrough | ⬜ | ⬜ | ⬜ | |

### Tier 2: Best Variants

| Kernel | Test | Benchmark | Leaderboard | Notes |
|--------|------|-----------|-------------|-------|
| moe_dispatch_policy | ⬜ | ⬜ | ⬜ | |
| moe_dispatch1_mask | ⬜ | ⬜ | ⬜ | |
| moe_baseline | ⬜ | ⬜ | ⬜ | |
| mla_best_final | ⬜ | ⬜ | ⬜ | |
| mla_fastmode | ⬜ | ⬜ | ⬜ | |
| mla_baseline | ⬜ | ⬜ | ⬜ | |
| gemm_baseline | ⬜ | ⬜ | ⬜ | |

## Summary

- Tier 1 Passing: X/3
- Tier 2 Passing: X/7
- Total Improved: X
- Best Result: 

EOF

# Replace date placeholder
sed -i "s/DATE_PLACEHOLDER/$(date)/g" "$RESULTS_FILE"

# Function to run test
run_test() {
    local kernel=$1
    local leaderboard=$2
    local tier=$3
    
    echo ""
    echo "----------------------------------------"
    echo "Testing: $kernel (Tier $tier)"
    echo "Leaderboard: $leaderboard"
    echo "Time: $(date)"
    echo "----------------------------------------"
    
    if [ -f "$kernel" ]; then
        echo "Running: popcorn run $kernel --mode test --leaderboard $leaderboard"
        if popcorn run "$kernel" --mode test --leaderboard "$leaderboard" 2>&1 | tee -a "$LOG_FILE"; then
            echo "✓ PASS: $kernel"
            echo "✓ PASS: $kernel" >> "$RESULTS_FILE"
            return 0
        else
            echo "✗ FAIL: $kernel"
            echo "✗ FAIL: $kernel" >> "$RESULTS_FILE"
            return 1
        fi
    else
        echo "✗ MISSING: $kernel"
        return 1
    fi
}

# ===========================================
# TIER 1: BREAKTHROUGH CANDIDATES
# ===========================================

echo ""
echo "=================================="
echo "TIER 1: BREAKTHROUGH CANDIDATES"
echo "=================================="

cd tier1_breakthrough

run_test "moe_breakthrough.py" "amd-moe-mxfp4" "1"
run_test "mla_breakthrough.py" "amd-mla-decode" "1"
run_test "gemm_breakthrough.py" "amd-mxfp4-mm" "1"

cd ..

# ===========================================
# TIER 2: BEST VARIANTS
# ===========================================

echo ""
echo "=================================="
echo "TIER 2: BEST VARIANTS"
echo "=================================="

cd tier2_best

run_test "moe_dispatch_policy.py" "amd-moe-mxfp4" "2"
run_test "moe_dispatch1_mask.py" "amd-moe-mxfp4" "2"
run_test "moe_baseline.py" "amd-moe-mxfp4" "2"
run_test "mla_best_final.py" "amd-mla-decode" "2"
run_test "mla_fastmode.py" "amd-mla-decode" "2"
run_test "mla_baseline.py" "amd-mla-decode" "2"
run_test "gemm_baseline.py" "amd-mxfp4-mm" "2"

cd ..

# ===========================================
# SUMMARY
# ===========================================

echo ""
echo "=================================="
echo "DEPLOYMENT COMPLETE"
echo "=================================="
echo "Completed: $(date)"
echo "Log file: $LOG_FILE"
echo "Results file: $RESULTS_FILE"
echo ""
echo "Next steps:"
echo "1. Review $RESULTS_FILE for passing kernels"
echo "2. Run benchmark mode on passing kernels:"
echo "   popcorn run <kernel> --mode benchmark --leaderboard <name>"
echo "3. Submit to leaderboard:"
echo "   popcorn run <kernel> --mode leaderboard --leaderboard <name>"
echo ""
echo "See README.md for full deployment strategy"
