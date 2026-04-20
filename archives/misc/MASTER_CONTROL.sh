#!/bin/bash
# MASTER_CONTROL.sh - Start and manage the overnight submission system

SCRIPT_DIR="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
LOG_DIR="/tmp/luma_master_control"
mkdir -p "$LOG_DIR"

show_help() {
    cat << EOF
Luma AMD Speedrun - Master Control

Usage: $0 <command> [options]

Commands:
  start           Start the production overnight system
  start-multi     Start 3 coordinated sessions (1 per kernel)
  stop            Stop all running sessions
  status          Show current status
  logs            Show recent logs
  once            Run one submission round and exit
  quick-check     Quick status check of all submissions

Options for start:
  -v, --verbose   Enable verbose logging
  -d, --detach    Run in background

Examples:
  $0 start                    # Start single robust session
  $0 start-multi             # Start 3 coordinated sessions
  $0 stop                    # Stop everything
  $0 status                  # Check status
  $0 once                    # Quick test

EOF
}

check_running() {
    local count=$(pgrep -f "PRODUCTION_OVERNIGHT_SYSTEM.sh" 2>/dev/null | wc -l)
    echo "$count"
}

start_production() {
    local detach=${1:-false}
    
    echo "Starting PRODUCTION overnight system..."
    
    cd "$SCRIPT_DIR"
    chmod +x PRODUCTION_OVERNIGHT_SYSTEM.sh
    
    if [[ "$detach" == "true" ]]; then
        nohup ./PRODUCTION_OVERNIGHT_SYSTEM.sh > "$LOG_DIR/production.log" 2>&1 &
        local pid=$!
        echo "$pid" > "$LOG_DIR/production.pid"
        echo "✅ Started in background (PID: $pid)"
        echo "   Log: $LOG_DIR/production.log"
    else
        ./PRODUCTION_OVERNIGHT_SYSTEM.sh
    fi
}

start_multi() {
    echo "Starting MULTI-SESSION coordinated system..."
    
    cd "$SCRIPT_DIR"
    chmod +x SESSION_COORDINATOR.sh
    
    # Start 3 coordinated sessions
    for i in 1 2 3; do
        nohup ./SESSION_COORDINATOR.sh > "$LOG_DIR/session_$i.log" 2>&1 &
        echo $! > "$LOG_DIR/session_$i.pid"
        echo "✅ Session $i started (PID: $!)"
        sleep 20  # Stagger starts
    done
    
    echo ""
    echo "All sessions started!"
    echo "Monitoring: tail -f $LOG_DIR/*.log"
}

stop_all() {
    echo "Stopping all overnight sessions..."
    
    # Stop production system
    pkill -f "PRODUCTION_OVERNIGHT_SYSTEM.sh" 2>/dev/null || true
    pkill -f "SESSION_COORDINATOR.sh" 2>/dev/null || true
    
    # Clean up locks
    rm -rf /tmp/luma_leaderboard_locks/* 2>/dev/null || true
    rm -rf /tmp/luma_coord/* 2>/dev/null || true
    
    echo "✅ All sessions stopped"
}

show_status() {
    echo "═══════════════════════════════════════════"
    echo "LUMA OVERNIGHT SYSTEM STATUS"
    echo "═══════════════════════════════════════════"
    echo "$(date)"
    echo ""
    
    # Show running processes
    local count=$(check_running)
    echo "Active sessions: $count"
    echo ""
    
    # Show recent submissions
    echo "Recent Submissions:"
    for lb in amd-mixed-mla amd-moe-mxfp4 amd-mxfp4-mm; do
        echo "  [$lb]"
        timeout 5 popcorn-cli submissions list --leaderboard "$lb" 2>&1 | tail -1 | sed 's/^/    /'
    done
    echo ""
    
    # Show rate limit status
    echo "Rate Limit Status:"
    for kernel in mla moe gemm; do
        local last_file="/tmp/luma_overnight_logs/last_${kernel}"
        if [[ -f "$last_file" ]]; then
            local last=$(cat "$last_file")
            local now=$(date +%s)
            local elapsed=$((now - last))
            local remaining=$((3600 - elapsed))
            
            if [[ $remaining -le 0 ]]; then
                echo "  $kernel: ✅ Ready to submit"
            else
                echo "  $kernel: ⏳ ${remaining}s remaining"
            fi
        else
            echo "  $kernel: ✅ No previous submission"
        fi
    done
    echo ""
    
    # Show recent log activity
    echo "Recent Activity:"
    if [[ -d "$LOG_DIR" ]]; then
        tail -10 "$LOG_DIR/coordinator.log" 2>/dev/null | sed 's/^/  /' || echo "  No logs yet"
    fi
    echo ""
    echo "═══════════════════════════════════════════"
}

show_logs() {
    echo "Recent logs:"
    
    if [[ -d "$LOG_DIR" ]]; then
        echo ""
        echo "--- Production Log (last 20 lines) ---"
        tail -20 "$LOG_DIR/production.log" 2>/dev/null || echo "  No production log"
        echo ""
        
        for i in 1 2 3; do
            if [[ -f "$LOG_DIR/session_$i.log" ]]; then
                echo "--- Session $i (last 10 lines) ---"
                tail -10 "$LOG_DIR/session_$i.log"
                echo ""
            fi
        done
    fi
    
    echo ""
    echo "--- Recent Popcorn Activity ---"
    ls -lt /tmp/luma_overnight_logs/*.log 2>/dev/null | head -3 | while read -r line; do
        echo "$line"
    done || echo "  No popcorn logs found"
}

run_once() {
    echo "Running ONE submission round..."
    cd "$SCRIPT_DIR"
    chmod +x PRODUCTION_OVERNIGHT_SYSTEM.sh
    ./PRODUCTION_OVERNIGHT_SYSTEM.sh once
}

quick_check() {
    echo "Quick Status Check"
    echo "=================="
    echo ""
    
    for lb in amd-mixed-mla amd-moe-mxfp4 amd-mxfp4-mm; do
        local latest=$(timeout 5 popcorn-cli submissions list --leaderboard "$lb" 2>&1 | sed -n '2p')
        if [[ -n "$latest" ]]; then
            local id=$(echo "$latest" | awk '{print $1}')
            local status=$(echo "$latest" | awk '{print $6}')
            local score=$(echo "$latest" | awk '{print $7}')
            echo "[$lb] $id [$status] Score: $score"
        fi
    done
}

# Main
case "${1:-help}" in
    start)
        start_production false
        ;;
    "start-daemon"|"start-bg")
        start_production true
        ;;
    "start-multi")
        start_multi
        ;;
    stop|kill|halt)
        stop_all
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    once)
        run_once
        ;;
    "quick-check"|check)
        quick_check
        ;;
    restart)
        stop_all
        sleep 2
        start_production
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
