#!/bin/bash
# EXECUTE ALL NIGHT - Win or Die Strategy
# Mission: Rank 1 on ALL kernels by April 6
# Email: manderson240@gmail.com on >5% improvement

set -e

echo "🔥🔥🔥 EXECUTE ALL NIGHT - $(date) 🔥🔥🔥"
echo ""
echo "Mission: Win Luma AMD Speedrun"
echo "Deadline: April 6, 2026 11:59 PM PST"
echo "Email: manderson240@gmail.com"
echo ""

# Kill any existing processes
pkill -f "popcorn" 2>/dev/null || true
pkill -f "WIN_OR_DIE" 2>/dev/null || true
sleep 2

BASE_DIR="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun"
LOG_DIR="/tmp/luma_night_$(date +%Y%m%d)"
mkdir -p "$LOG_DIR"

# Function: Send email
send_email() {
    local subject="$1"
    local body="$2"
    echo "$body" | mail -s "$subject" manderson240@gmail.com 2>/dev/null || echo "Email failed"
    echo "📧 Email sent: $subject"
}

# Function: Run test mode (unlimited)
run_test() {
    local kernel=$1
    local file=$2
    local leaderboard=$3
    
    echo ""
    echo "🔬 TESTING $kernel..."
    timeout 180 popcorn-cli submit "$file" --mode test --gpu MI355X --leaderboard "$leaderboard" --no-tui 2>&1 | tee "$LOG_DIR/${kernel}_test.log" || true
    
    if grep -q "Testing successful" "$LOG_DIR/${kernel}_test.log"; then
        echo "✅ $kernel TEST PASSED"
        return 0
    else
        echo "❌ $kernel TEST FAILED"
        return 1
    fi
}

# Function: Run benchmark mode (unlimited)
run_benchmark() {
    local kernel=$1
    local file=$2
    local leaderboard=$3
    
    echo ""
    echo "⏱️  BENCHMARKING $kernel..."
    timeout 300 popcorn-cli submit "$file" --mode benchmark --gpu MI355X --leaderboard "$leaderboard" --no-tui 2>&1 | tee "$LOG_DIR/${kernel}_benchmark.log" || true
    
    # Extract timing
    local timing=$(grep -oE '[0-9]+\.[0-9]+\s*±' "$LOG_DIR/${kernel}_benchmark.log" | head -1 | grep -oE '[0-9]+\.[0-9]+' || echo "0")
    echo "⏱️  $kernel timing: ${timing}µs"
    
    if grep -q "Benchmarking successful" "$LOG_DIR/${kernel}_benchmark.log"; then
        echo "✅ $kernel BENCHMARK SUCCESS"
        return 0
    else
        echo "⚠️  $kernel BENCHMARK ISSUE"
        return 1
    fi
}

# Function: Submit to leaderboard (rate limited)
run_leaderboard() {
    local kernel=$1
    local file=$2
    local leaderboard=$3
    
    echo ""
    echo "🚀 SUBMITTING $kernel TO LEADERBOARD..."
    timeout 300 popcorn-cli submit "$file" --mode leaderboard --gpu MI355X --leaderboard "$leaderboard" --no-tui 2>&1 | tee "$LOG_DIR/${kernel}_leaderboard.log" || true
    
    if grep -q "Leaderboard run successful" "$LOG_DIR/${kernel}_leaderboard.log"; then
        echo "✅ $kernel LEADERBOARD SUBMITTED!"
        
        # Victory check
        if [ "$kernel" = "moe" ]; then
            send_email "🏆 BREAKTHROUGH: MoE Submitted!" "MoE submitted successfully at $(date). Check leaderboard for ranking."
        fi
        return 0
    elif grep -q "Rate limit exceeded" "$LOG_DIR/${kernel}_leaderboard.log"; then
        echo "⏳ $kernel RATE LIMITED - will retry later"
        return 1
    else
        echo "❌ $kernel LEADERBOARD FAILED"
        return 1
    fi
}

# Main execution loop
CYCLE=0
while true; do
    CYCLE=$((CYCLE + 1))
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "CYCLE $CYCLE - $(date)"
    echo "═══════════════════════════════════════════════════"
    
    # MoE (already submitted, check if we can resubmit improved version)
    echo ""
    echo "🎯 MoE STATUS: Already submitted 93.4µs"
    
    # MLA - Test -> Benchmark -> Submit
    echo ""
    echo "🔥 PRIORITY 1: MLA"
    run_test "mla" "$BASE_DIR/amd-mixed-mla/submission.py" "amd-mixed-mla" && \
    run_benchmark "mla" "$BASE_DIR/amd-mixed-mla/submission.py" "amd-mixed-mla" && \
    run_leaderboard "mla" "$BASE_DIR/amd-mixed-mla/submission.py" "amd-mixed-mla"
    
    # GEMM - Test -> Benchmark -> Submit
    echo ""
    echo "🔥 PRIORITY 2: GEMM"
    run_test "gemm" "$BASE_DIR/amd-mxfp4-mm/submission.py" "amd-mxfp4-mm" && \
    run_benchmark "gemm" "$BASE_DIR/amd-mxfp4-mm/submission.py" "amd-mxfp4-mm" && \
    run_leaderboard "gemm" "$BASE_DIR/amd-mxfp4-mm/submission.py" "amd-mxfp4-mm"
    
    # Check for victories
    echo ""
    echo "📊 VICTORY CHECK"
    echo "  MoE: 93.4µs vs Rank 1 target 107.345µs"
    echo "  MLA: See logs above"
    echo "  GEMM: See logs above"
    
    # Wait before next cycle (respect rate limits)
    echo ""
    echo "😴 Sleeping 120 seconds before next cycle..."
    sleep 120
done
