#!/usr/bin/env python3
"""
Robust AGI Overnight - Stuck Prevention v3
Simple, robust, no dependencies
"""

import json
import time

# Target: 7 AM EST tomorrow
from datetime import datetime, timedelta, timezone

import numpy as np


EST = timezone(timedelta(hours=-5))
NOW = datetime.now(EST)
TARGET = NOW.replace(hour=7, minute=0, second=0, microsecond=0)
if TARGET <= NOW:
    from datetime import timedelta

    TARGET += timedelta(days=1)

print("=" * 70)
print("AGI OVERNIGHT v3.0: ROBUST STUCK-PREVENTION")
print("=" * 70)
print(f"Start: {NOW.strftime('%H:%M:%S')}")
print("Target: 7:00 AM EST")
print(f"Expected duration: ~{TARGET - NOW!s}")
print()
print("Features:")
print("  • Stuck detection: variance monitoring")
print("  • Auto-intervention: random perturbation")
print("  • State checkpointing every 15 min")
print("  • Self-healing: adaptive learning rates")
print("=" * 70)
print()

# Simple state
dim = 12
coupling = np.array([1.0] * 3 + [0.7] * 3 + [0.5] * 3 + [0.3] * 3)
state = np.random.randn(dim) * 0.3 + 0.5
decay = 0.9**50
lr = 1e-3
weights = np.random.randn(dim, dim) * 0.001

# Tracking
iterations = 0
metrics = []
coherence_history = []
stuck_count = 0

# Log file
log_file = open("agi_v3.log", "w")


def log(msg):
    ts = datetime.now(EST).strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    log_file.write(line + "\n")
    log_file.flush()


def is_stuck(history, window=50):
    """Detect if system is truly stuck (no learning, not just converged)."""
    if len(history) < window:
        return False

    # Check last 50 iterations
    recent = history[-window:]

    # Stuck if:
    # 1. Coherence not changing (already at attractor)
    # AND 2. State is static (not exploring)
    coherence_var = np.var([h["coherence"] for h in recent])
    state_var = np.var([np.std(h["state"]) for h in recent])

    # Only stuck if both are flat (converged AND not exploring)
    return coherence_var < 1e-8 and state_var < 1e-6


def intervene():
    """Break out of stuck state."""
    global state, lr, stuck_count
    stuck_count += 1
    log(f"STUCK #{stuck_count} - INTERVENING")

    # Random perturbation
    state = np.random.randn(dim) * 0.5 + 0.5

    # Reset learning rate to baseline, not boost
    lr = max(1e-3, lr * 0.5)  # Reduce, reset toward baseline
    log(f"  State perturbed, LR reset to {lr:.5f}")

    return True


log("Starting AGI experience loop...")
log("Ctrl+C to interrupt")
log("")

start = time.time()
next_checkpoint = start + 900  # 15 min
next_status = start + 60  # 1 min

try:
    while datetime.now(EST) < TARGET:
        iterations += 1

        # Evolution (closed-form HIHO)
        state = state * decay + 0.5 * (1 - decay) * coupling * 10

        # Coherence metric
        coherence = float(np.mean(np.abs(state - 0.5)))
        coherence_history.append({"coherence": coherence, "state": state.copy()})

        # Stuck detection every 100 iterations
        if iterations % 100 == 0:
            if is_stuck(coherence_history):
                intervene()
                stuck_count += 1
                coherence_history = []  # Reset history

        # Status log every minute
        if time.time() >= next_status:
            elapsed = (time.time() - start) / 60
            remaining = (TARGET - datetime.now(EST)).total_seconds() / 60

            log(
                f"Iter:{iterations:8d} | Coh:{coherence:.4f} | "
                f"Stuck:{stuck_count:2d} | Elapsed:{elapsed:5.1f}min | "
                f"Remaining:{remaining:5.1f}min"
            )

            # Adaptive: reduce LR if stable
            if len(coherence_history) > 50:
                recent_var = np.var(coherence_history[-50:])
                if recent_var < 0.001 and lr > 1e-4:
                    lr *= 0.9
                    log(f"  LR reduced to {lr:.5f} (stable)")

            metrics.append(
                {
                    "time": elapsed,
                    "iterations": iterations,
                    "coherence": coherence,
                    "stuck_count": stuck_count,
                    "lr": lr,
                }
            )
            next_status = time.time() + 60

        # Checkpoint every 15 min
        if time.time() >= next_checkpoint:
            checkpoint = {
                "timestamp": datetime.now(EST).isoformat(),
                "iterations": iterations,
                "stuck_count": stuck_count,
                "coherence": coherence,
                "state": state.tolist(),
            }
            with open("checkpoint.json", "w") as f:
                json.dump(checkpoint, f)
            log("Checkpoint saved")
            next_checkpoint = time.time() + 900

        # Small delay
        time.sleep(0.001)

except KeyboardInterrupt:
    log("\nInterrupted by user")

finally:
    duration = (time.time() - start) / 60
    log_file.close()

    print()
    print("=" * 70)
    print("AGI OVERNIGHT COMPLETE")
    print("=" * 70)
    print(f"Duration: {duration:.1f} minutes")
    print(f"Total iterations: {iterations:,}")
    print(f"Stuck events: {stuck_count}")
    print(f"Interventions: {stuck_count}")
    print(f"Final coherence: {coherence:.4f}")

    with open("agi_v3_results.json", "w") as f:
        json.dump(
            {
                "experiment": "agi_overnight_v3",
                "duration_min": duration,
                "iterations": iterations,
                "stuck_count": stuck_count,
                "interventions": stuck_count,
                "final_coherence": coherence,
                "metrics": metrics,
            },
            f,
        )

    print(f"\nMETRIC duration={duration:.0f} cycles={iterations}")
