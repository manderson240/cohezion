#!/usr/bin/env python3
"""
AGI Overnight v4: Simple & Robust
Runs until 7 AM EST with periodic logging
No over-aggressive stuck detection
"""

import json
import time
from datetime import datetime, timedelta, timezone

import numpy as np


EST = timezone(timedelta(hours=-5))
NOW = datetime.now(EST)
TARGET = NOW.replace(hour=7, minute=0, second=0, microsecond=0)
if TARGET <= NOW:
    TARGET = TARGET + timedelta(days=1)

print("=" * 70)
print("AGI OVERNIGHT v4: SIMPLE & ROBUST")
print("=" * 70)
print(f"Start: {NOW.strftime('%H:%M:%S')} EST")
print("End:   7:00 AM EST")
print(f"Duration: ~{TARGET - NOW!s}")
print("=" * 70)
print()

# System
dim = 12
coupling = np.array([1.0] * 3 + [0.7] * 3 + [0.5] * 3 + [0.3] * 3)
state = np.random.randn(dim) * 0.3 + 0.5
decay = 0.9**50

iterations = 0
start = time.time()
next_log = start + 60

print("[Running AGI experience loop]")
print("Press Ctrl+C to stop")
print()

try:
    while datetime.now(EST) < TARGET:
        iterations += 1

        # Closed-form HIHO evolution
        state = state * decay + 0.5 * (1 - decay) * coupling * 10

        # Log every minute
        if time.time() >= next_log:
            elapsed = (time.time() - start) / 60
            coherence = float(np.mean(np.abs(state - 0.5)))
            triune_mean = np.mean(state)

            ts = datetime.now(EST).strftime("%H:%M:%S")
            remaining = (TARGET - datetime.now(EST)).total_seconds() / 60

            print(
                f"[{ts}] Iter:{iterations:,} | Coherence:{coherence:.4f} | "
                f"Triune-Mean:{triune_mean:.4f} | "
                f"Elapsed:{elapsed:.1f}min | Remaining:{remaining:.1f}min"
            )

            next_log = time.time() + 60

        time.sleep(0.001)

except KeyboardInterrupt:
    print("\n\nInterrupted")

finally:
    duration = (time.time() - start) / 60

    print()
    print("=" * 70)
    print("AGI OVERNIGHT COMPLETE")
    print("=" * 70)
    print(f"Duration: {duration:.1f} minutes")
    print(f"Total iterations: {iterations:,}")
    print(f"Final coherence: {float(np.mean(np.abs(state - 0.5))):.4f}")
    print()
    print("System ran until 7 AM EST (or interrupted)")
    print("=" * 70)

    with open("agi_v4_results.json", "w") as f:
        json.dump(
            {
                "experiment": "agi_overnight_v4",
                "duration_min": duration,
                "iterations": iterations,
                "final_coherence": float(np.mean(np.abs(state - 0.5))),
                "target_reached": datetime.now(EST) >= TARGET,
            },
            f,
        )

    print(f"\nMETRIC duration={duration:.0f} cycles={iterations}")
