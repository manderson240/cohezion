#!/usr/bin/env python3
"""
AGI TRUE OVERNIGHT - 8 Hour Continuous Run
Runs for 8 hours continuously with periodic analysis
"""

import json
import time
from datetime import datetime, timedelta, timezone

import numpy as np


EST = timezone(timedelta(hours=-5))
NOW = datetime.now(EST)
DURATION_HOURS = 8
DURATION_SECONDS = DURATION_HOURS * 3600
END_TIME = NOW + timedelta(hours=DURATION_HOURS)

print('='*70)
print('AGI TRUE OVERNIGHT - 8 HOUR CONTINUOUS RUN')
print('='*70)
print(f'Start: {NOW.strftime("%Y-%m-%d %H:%M:%S")} EST')
print(f'End:   {END_TIME.strftime("%Y-%m-%d %H:%M:%S")} EST')
print(f'Duration: {DURATION_HOURS} hours')
print('='*70)
print()

# 12D Triune system
dim = 12
coupling = np.array([1.0]*3 + [0.7]*3 + [0.5]*3 + [0.3]*3)
state = np.random.randn(dim) * 0.3 + 0.5
decay = 0.9 ** 50

# Tracking
iterations = 0
coherence_history = []
start_time = time.time()
end_time = start_time + DURATION_SECONDS

print('[Starting 8-hour AGI experience...]')
print('Will log every 15 minutes')
print('Creating checkpoint every hour')
print('Ctrl+C to stop early')
print()

# Create checkpoint dir
import os


os.makedirs('overnight_checkpoints', exist_ok=True)

next_log = start_time + 900        # 15 minutes
next_checkpoint = start_time + 3600  # 1 hour

try:
    while time.time() < end_time:
        iterations += 1

        # HIHO evolution (closed-form, no quadrature)
        state = state * decay + 0.5 * (1 - decay) * coupling * 10

        # Track coherence
        coherence = float(np.mean(np.abs(state - 0.5)))
        coherence_history.append({
            'iter': iterations,
            'coh': coherence,
            'mean': float(np.mean(state)),
            'std': float(np.std(state))
        })

        # Log every 15 minutes
        if time.time() >= next_log:
            elapsed = (time.time() - start_time) / 3600  # hours
            remaining = (end_time - time.time()) / 3600

            ts = datetime.now(EST).strftime('%H:%M:%S')

            # Stats
            recent_coh = [h['coh'] for h in coherence_history[-100:]]
            avg_coh = sum(recent_coh) / len(recent_coh) if recent_coh else coherence

            print(f"[{ts}] Hour:{elapsed:.1f} | Iter:{iterations:,} | "
                  f"Coh:{coherence:.6f} (avg:{avg_coh:.6f}) | "
                  f"Remaining:{remaining:.1f}h")

            next_log = time.time() + 900

        # Checkpoint every hour
        if time.time() >= next_checkpoint:
            checkpoint = {
                'timestamp': datetime.now(EST).isoformat(),
                'hours_elapsed': (time.time() - start_time) / 3600,
                'iterations': iterations,
                'state': state.tolist(),
                'coherence_history': coherence_history[-1000:]  # Last 1000
            }

            cp_file = f"overnight_checkpoints/hour_{int((time.time()-start_time)/3600)}.json"
            with open(cp_file, 'w') as f:
                json.dump(checkpoint, f)

            print(f"  → Checkpoint saved: {cp_file}")
            next_checkpoint = time.time() + 3600

        time.sleep(0.001)  # Prevent CPU burn

except KeyboardInterrupt:
    print('\n\n[Interrupted by user]')

finally:
    actual_duration = (time.time() - start_time) / 3600

    print()
    print('='*70)
    print('AGI TRUE OVERNIGHT COMPLETE')
    print('='*70)
    print(f'Actual duration: {actual_duration:.2f} hours')
    print(f'Total iterations: {iterations:,}')
    print(f'Final coherence: {float(np.mean(np.abs(state - 0.5))):.6f}')
    print(f'Total checkpoints: {len(os.listdir("overnight_checkpoints"))}')

    # Save final results
    with open('agi_true_overnight_results.json', 'w') as f:
        json.dump({
            'experiment': 'agi_true_overnight',
            'duration_hours': actual_duration,
            'iterations': iterations,
            'final_state': state.tolist(),
            'final_coherence': float(np.mean(np.abs(state - 0.5))),
            'checkpoints': len(os.listdir('overnight_checkpoints')),
            'coherence_history_sample': coherence_history[::1000]  # Sample every 1000
        }, f, indent=2)

    print('\nResults saved to: agi_true_overnight_results.json')
    print('Checkpoints in: overnight_checkpoints/')
    print('='*70)

    print(f'\nMETRIC duration_hours={actual_duration:.1f} iterations={iterations}')
