#!/bin/bash
# =============================================================================
# Cohezion - SurrealDB Test Runner
# Enhanced test runner with Docker integration, parallel execution, and CI support
#
# Usage:
#   ./scripts/run-surreal-tests.sh [options] [pytest_args...]
#
# Options:
#   --keep              Keep container running after tests (for debugging)
#   --fast              Run only fast unit tests (no container needed)
#   --integration       Run integration tests only
#   --benchmark         Run benchmark tests
#   --live              Run live tests (requires external SurrealDB)
#   --all               Run full test suite (default)
#   --ci                CI mode (parallel execution, XML reports)
#   --parallel N        Run with N parallel workers (default: auto)
#   --coverage          Generate coverage reports
#   --verbose, -v       Verbose output
#   --help, -h          Show this help message
#
# Environment Variables:
#   SURREAL_URL         SurrealDB endpoint (default: ws://localhost:8000/rpc)
#   SURREAL_USER        SurrealDB username (default: root)
#   SURREAL_PASS        SurrealDB password (default: root)
#   SURREAL_NAMESPACE   SurrealDB namespace (default: test)
#   SURREAL_DATABASE    SurrealDB database (default: test)
#
# Examples:
#   ./scripts/run-surreal-tests.sh --fast
#   ./scripts/run-surreal-tests.sh --integration --parallel 4
#   ./scripts/run-surreal-tests.sh --ci --coverage
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker/surrealdb-test.yml"
CONTAINER_NAME="cohezion-surrealdb-test"

# Default settings
KEEP_CONTAINER=false
TEST_MODE="all"
CI_MODE=false
PARALLEL_WORKERS="auto"
COVERAGE=false
VERBOSE=false
PYTEST_ARGS=()

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# =============================================================================
# Utility Functions
# =============================================================================
print_header() {
    echo ""
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_section() {
    echo ""
    echo -e "${BOLD}▶ $1${NC}"
}

# =============================================================================
# Environment Setup
# =============================================================================
load_env() {
    # Load .env if available
    if [ -f "$PROJECT_ROOT/.env" ]; then
        set -a
        source "$PROJECT_ROOT/.env"
        set +a
    fi

    # Set defaults
    export SURREAL_URL="${SURREAL_URL:-ws://localhost:8000/rpc}"
    export SURREAL_USER="${SURREAL_USER:-root}"
    export SURREAL_PASS="${SURREAL_PASS:-root}"
    export SURREAL_NAMESPACE="${SURREAL_NAMESPACE:-test}"
    export SURREAL_DATABASE="${SURREAL_DATABASE:-test}"
}

# =============================================================================
# Prerequisites Check
# =============================================================================
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi

    print_success "Docker is available"
}

check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    UV_VERSION=$(uv --version | head -1 | cut -d' ' -f2)
    print_success "uv v${UV_VERSION} is available"
}

check_prerequisites() {
    print_section "Checking Prerequisites"
    check_uv

    case "$TEST_MODE" in
        integration|all)
            check_docker
            ;;
        live)
            # No Docker needed for live tests
            ;;
    esac
}

# =============================================================================
# SurrealDB Container Management
# =============================================================================
start_surrealdb() {
    print_section "Starting SurrealDB Container"

    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi

    # Create data directory if needed
    mkdir -p "$PROJECT_ROOT/data/surreal-test"

    # Stop any existing container
    print_status "Stopping existing containers..."
    docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true

    # Start fresh container
    print_status "Starting SurrealDB v2.0..."
    docker compose -f "$COMPOSE_FILE" up -d surrealdb

    # Wait for health check
    print_status "Waiting for SurrealDB to be ready..."
    local retries=0
    local max_retries=30

    while [ $retries -lt $max_retries ]; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            print_success "SurrealDB is ready"
            return 0
        fi
        echo -n "."
        sleep 2
        retries=$((retries + 1))
    done

    print_error "SurrealDB failed to start within $((max_retries * 2)) seconds"
    docker compose -f "$COMPOSE_FILE" logs --tail 50 surrealdb
    exit 1
}

stop_surrealdb() {
    if [ "$KEEP_CONTAINER" = true ]; then
        print_warning "Keeping container running (--keep specified)"
        print_status "Container '$CONTAINER_NAME' is running on port 8000"
        print_status "To stop: docker compose -f $COMPOSE_FILE down -v"
    else
        print_section "Stopping SurrealDB"
        docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
        print_success "Container stopped"
    fi
}

check_existing_container() {
    if docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_warning "Container '$CONTAINER_NAME' is already running"
        print_status "Reusing existing container on port 8000"
        return 0
    fi
    return 1
}

# =============================================================================
# Test Execution
# =============================================================================
run_pytest() {
    local marker="$1"
    shift
    local test_paths="${1:-tests/}"
    shift || true

    print_section "Running Pytest"
    print_status "Marker: $marker"
    print_status "Paths: $test_paths"

    # Build pytest command
    local pytest_cmd=("uv" "run" "pytest" "-m" "$marker")

    # Add parallel execution for CI or explicit --parallel
    if [ "$CI_MODE" = true ] || [ "$PARALLEL_WORKERS" != "1" ]; then
        if [ "$PARALLEL_WORKERS" = "auto" ]; then
            pytest_cmd+=("-n" "auto")
        else
            pytest_cmd+=("-n" "$PARALLEL_WORKERS")
        fi
        pytest_cmd+=("--dist" "loadgroup")
    fi

    # Add coverage
    if [ "$COVERAGE" = true ]; then
        pytest_cmd+=(
            "--cov=src/cohezion"
            "--cov-report=xml:coverage-${marker}.xml"
            "--cov-report=html:htmlcov-${marker}/"
            "--cov-report=term-missing"
        )
    fi

    # Add CI-specific outputs
    if [ "$CI_MODE" = true ]; then
        pytest_cmd+=("--junitxml=junit-${marker}.xml")
    fi

    # Add verbose mode
    if [ "$VERBOSE" = true ]; then
        pytest_cmd+=("-vvv")
    else
        pytest_cmd+=("-v")
    fi

    # Add traceback
    pytest_cmd+=("--tb=short")

    # Add test paths
    pytest_cmd+=($test_paths)

    # Add extra pytest args
    if [ ${#PYTEST_ARGS[@]} -gt 0 ]; then
        pytest_cmd+=("${PYTEST_ARGS[@]}")
    fi

    # Show command
    print_status "Command: ${pytest_cmd[*]}"

    # Export environment
    export SURREAL_URL
    export SURREAL_USER
    export SURREAL_PASS
    export SURREAL_NAMESPACE
    export SURREAL_DATABASE
    export TEST_WITH_LIVE_DB="1"

    cd "$PROJECT_ROOT"

    # Run tests
    if ! "${pytest_cmd[@]}"; then
        print_error "Tests failed"
        return 1
    fi

    print_success "Tests passed"
}

run_fast_tests() {
    print_header "FAST UNIT TESTS"
    print_status "Running fast tests (<1s each, no external services)"

    run_pytest "fast" "tests/unit/ tests/persistence/"
}

run_integration_tests() {
    print_header "INTEGRATION TESTS"
    print_status "Running with SurrealDB container"

    # Start container if needed
    if ! check_existing_container; then
        start_surrealdb
    fi

    # Set trap to stop container on exit (unless --keep)
    if [ "$KEEP_CONTAINER" = false ]; then
        trap stop_surrealdb EXIT
    fi

    run_pytest "integration" "tests/integration/"
}

run_benchmark_tests() {
    print_header "BENCHMARK TESTS"
    print_status "Running performance benchmarks"

    cd "$PROJECT_ROOT"

    local pytest_cmd=("uv" "run" "pytest" "-m" "benchmark")

    if [ "$CI_MODE" = true ]; then
        pytest_cmd+=("--benchmark-json=benchmark-results.json")
    fi

    pytest_cmd+=("--benchmark-only" "-v" "--tb=short")

    if [ ${#PYTEST_ARGS[@]} -gt 0 ]; then
        pytest_cmd+=("${PYTEST_ARGS[@]}")
    fi

    "${pytest_cmd[@]}"
}

run_live_tests() {
    print_header "LIVE TESTS"
    print_status "Running against external SurrealDB"
    print_status "URL: $SURREAL_URL"

    # Verify connection
    local health_url="${SURREAL_URL/ws/http}"
    if ! curl -sf "${health_url}/health" > /dev/null 2>&1; then
        print_warning "Cannot connect to SurrealDB at $SURREAL_URL"
        print_status "Make sure your external SurrealDB is running"
        # Don't fail - may be expected in some environments
    else
        print_success "Connected to external SurrealDB"
    fi

    run_pytest "live" "tests/"
}

run_all_tests() {
    print_header "FULL TEST SUITE"

    # Phase 1: Fast tests
    print_section "Phase 1: Fast Unit Tests"
    run_fast_tests

    # Phase 2: Integration tests (with container)
    print_section "Phase 2: Integration Tests"

    if ! check_existing_container; then
        start_surrealdb
        trap stop_surrealdb EXIT
    fi

    run_integration_tests

    # Phase 3: Benchmark tests (optional)
    if [ "$CI_MODE" = false ]; then
        print_section "Phase 3: Benchmark Tests"
        run_benchmark_tests || print_warning "Benchmark tests had issues"
    fi

    print_success "All tests complete!"
}

# =============================================================================
# Results Reporting
# =============================================================================
show_results() {
    if [ "$CI_MODE" = true ]; then
        print_section "Test Artifacts"

        # List generated files
        if ls junit-*.xml > /dev/null 2>&1; then
            print_status "JUnit reports:"
            ls -lh junit-*.xml | awk '{print "  - " $9 " (" $5 ")"}'
        fi

        if ls coverage-*.xml > /dev/null 2>&1; then
            print_status "Coverage reports:"
            ls -lh coverage-*.xml | awk '{print "  - " $9 " (" $5 ")"}'
        fi

        if [ -f benchmark-results.json ]; then
            print_status "Benchmark results: benchmark-results.json"
        fi

        # Coverage summary
        if ls htmlcov-* > /dev/null 2>&1; then
            print_status "HTML coverage reports available in:"
            ls -d htmlcov-* | sed 's/^/  - /'
        fi
    fi
}

# =============================================================================
# Help
# =============================================================================
show_help() {
    sed -n '/^# ==/,/^# ==/p' "$0" | sed 's/^# //'
}

# =============================================================================
# Argument Parsing
# =============================================================================
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --keep)
                KEEP_CONTAINER=true
                shift
                ;;
            --fast)
                TEST_MODE="fast"
                shift
                ;;
            --integration)
                TEST_MODE="integration"
                shift
                ;;
            --benchmark)
                TEST_MODE="benchmark"
                shift
                ;;
            --live)
                TEST_MODE="live"
                shift
                ;;
            --all)
                TEST_MODE="all"
                shift
                ;;
            --ci)
                CI_MODE=true
                shift
                ;;
            --parallel)
                PARALLEL_WORKERS="$2"
                shift 2
                ;;
            --coverage)
                COVERAGE=true
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*)
                # Pass through unknown args to pytest
                PYTEST_ARGS+=("$1")
                shift
                ;;
            *)
                # Pass through positional args to pytest
                PYTEST_ARGS+=("$1")
                shift
                ;;
        esac
    done
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    parse_args "$@"
    load_env

    print_header "SurrealDB Test Runner"
    print_status "Mode: ${TEST_MODE}"
    print_status "CI Mode: ${CI_MODE}"
    print_status "Parallel: ${PARALLEL_WORKERS}"
    print_status "Coverage: ${COVERAGE}"

    check_prerequisites

    case $TEST_MODE in
        fast)
            run_fast_tests
            ;;
        integration)
            run_integration_tests
            ;;
        benchmark)
            run_benchmark_tests
            ;;
        live)
            run_live_tests
            ;;
        all)
            run_all_tests
            ;;
        *)
            print_error "Unknown test mode: $TEST_MODE"
            exit 1
            ;;
    esac

    show_results
    print_success "Done!"
}

# Run main
main "$@"
