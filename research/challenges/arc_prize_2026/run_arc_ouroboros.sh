#!/usr/bin/env bash
# ARC Prize 2026 - Overnight Ouroboros Loop
# Runs all ARC tracks continuously to generate experiential knowledge
# and allows Ouroboros to heal/improve the system until 7 AM EST.

echo "Starting ARC Ouroboros Overnight Loop..."
echo "Target completion: 7:00 AM EST (07:00:00)"

# Start Ouroboros Daemon in the background if it's not running
if ! pgrep -f "start_ouroboros.py" > /dev/null; then
    echo "Starting Ouroboros Daemon..."
    export PYTHONPATH=src
    uv run --no-project --python 3.12 --with websockets --with structlog --with httpx --with pydantic --with pydantic-settings python3 scripts/drivers/start_ouroboros.py &
    OUROBOROS_PID=$!
    sleep 5
else
    echo "Ouroboros Daemon is already running."
fi

# Loop until 7:00 AM EST
while true; do
    # Get current time in EST
    CURRENT_TIME=$(TZ="America/New_York" date +%H%M)
    
    # Check if we have reached 07:00 AM (0700)
    if [ "$CURRENT_TIME" -ge "0700" ] && [ "$CURRENT_TIME" -lt "0800" ]; then
        echo "Reached 7:00 AM EST. Terminating overnight loop."
        break
    fi
    
    echo "Current time (EST): $(TZ="America/New_York" date +%H:%M:%S) - Continuing experiential loops..."
    
    # 1. TDD: Running Unit Tests (Ensuring 100% Integrity)
    echo "--- [TDD] Running ARC JEPA Unit Tests ---"
    uv run --no-project --python 3.12 --with numpy --with torch python3 research/challenges/arc_prize_2026/run_unit_tests.py || echo "TDD Failed, continuing to Ouroboros analysis..."

    # 2. ARC-AGI-3: Topological Navigation (Generates Latent Trajectories for Ouroboros)
    echo "--- Running ARC-AGI-3 Topological Navigation ---"
    export PYTHONPATH=src:research/challenges/arc_prize_2026
    uv run --no-project --python 3.12 --with numpy --with arc-agi>=0.9.3 --with gymnasium --with torch --with scipy --with httpx --with pydantic --with pydantic-settings --with structlog python3 research/challenges/arc_prize_2026/arc_topology_navigation.py || echo "Navigation encountered an error, continuing..."

    # 3. ARC-AGI-2: Cosmogonic Program Synthesis (Generates Rules)
    echo "--- Running ARC-AGI-2 Cosmogonic Evaluator ---"
    export PYTHONPATH=src:research/challenges/arc_prize_2026
    uv run --no-project --python 3.12 --with numpy --with torch --with httpx --with pydantic --with pydantic-settings --with structlog python3 research/challenges/arc_prize_2026/evaluate_cosmogony.py || echo "Evaluator encountered an error, continuing..."

    # 4. [Adversarial Review] Evaluate System Integrity
    echo "--- [Adversarial] Running Multi-Perspective Review ---"
    uv run --no-project --python 3.12 --with numpy --with structlog --with httpx --with pydantic --with pydantic-settings env PYTHONPATH=src python3 research/challenges/arc_prize_2026/run_adversarial_review.py || echo "Adversarial Review failed, continuing..."

    # 5. ARC-AGI Task Generation (Evo HIHO Benchmark)
    echo "--- Running ARC-AGI Synthetic Task Generation ---"
    export PYTHONPATH=src
    uv run --no-project --python 3.12 --with numpy --with structlog --with pydantic --with pydantic-settings --with httpx python3 kaggle-agi-benchmark/generate_evo_hiho_tasks.py --num_tasks 5 || echo "Generator encountered an error, continuing..."

    
    # Let Ouroboros digest the SurrealDB logs
    echo "--- Ouroboros Digesting... ---"
    sleep 30
done

if [ -n "${OUROBOROS_PID:-}" ]; then
    echo "Stopping Ouroboros Daemon (PID: $OUROBOROS_PID)..."
    kill $OUROBOROS_PID
fi

echo "Overnight loop successfully completed!"
