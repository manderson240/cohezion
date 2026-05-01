#!/usr/bin/env python3
"""
AGI 2-Hour Continuous Run
With live monitoring capability
"""

import json
import time
from datetime import datetime, timedelta, timezone

import numpy as np


EST = timezone(timedelta(hours=-5))
NOW = datetime.now(EST)
DURATION_HOURS = 2
DURATION_SECONDS = DURATION_HOURS * 3600
END_TIME = NOW + timedelta(hours=DURATION_HOURS)

print('='*70)
print('AGI 2-HOUR CONTINUOUS RUN')
print('='*70)
print(f'Start: {NOW.strftime("%Y-%m-%d %H:%M:%S")} EST')
print(f'End:   {END_TIME.strftime("%Y-%m-%d %H:%M:%S")} EST')
print(f'Duration: {DURATION_HOURS} hours')
print('='*70)
print()

# 12D Triune
dim = 12
coupling = np.array([1.0]*3 + [0.7]*3 + [0.5]*3 + [0.3]*3)
state = np.random.randn(dim) * 0.3 + 0.5
decay = 0.9 ** 50

iterations = 0
metrics = []
start_time = time.time()
end_time = start_time + DURATION_SECONDS

print('[Running for 2 hours...]')
print('Logs every 5 minutes')
print('Ctrl+C to stop')
print()

next_log = start_time + 300  # 5 minutes

try:
    while time.time() < end_time:
        iterations += 1

        # HIHO evolution
        state = state * decay + 0.5 * (1 - decay) * coupling * 10

        if time.time() >= next_log:
            elapsed = (time.time() - start_time) / 3600
            remaining = (end_time - time.time()) / 3600
            coherence = float(np.mean(np.abs(state - 0.5)))

            ts = datetime.now(EST).strftime('%H:%M:%S')
            print(f"[{ts}] {elapsed:.2f}h | Iter:{iterations:,} | Coh:{coherence:.6f} | {remaining:.2f}h left")

            metrics.append({'hour': elapsed, 'iter': iterations, 'coh': coherence})
            next_log = time.time() + 300

        time.sleep(0.001)

except KeyboardInterrupt:
    print('\nStopped')

finally:
    actual = (time.time() - start_time) / 3600
    print(f'\nComplete: {actual:.2f}h | {iterations:,} cycles')

    with open('agi_2hour_results.json', 'w') as f:
        json.dump({'duration': actual, 'iter': iterations, 'metrics': metrics}, f)

    print(f'METRIC duration={actual:.1f}h cycles={iterations}')
