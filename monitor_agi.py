#!/usr/bin/env python3
"""
Live Monitor for AGI Overnight Experiment
Analyzes output and provides insights as experiment runs
"""

import json
import os
import time
from datetime import datetime


log_file = 'agi_v4.log'
results_file = 'agi_v4_results.json'

print('='*70)
print('AGI OVERNIGHT - LIVE MONITOR')
print('='*70)
print('Reading from:', log_file)
print('Analysis every 30 seconds')
print('='*70)
print()

cycles = 0
coherence_values = []
start_time = time.time()
last_size = 0

def analyze_state():
    """Analyze current AGI state."""
    global cycles, coherence_values, last_size

    if not os.path.exists(log_file):
        return None

    current_size = os.path.getsize(log_file)
    if current_size == last_size:
        return None  # No new data

    last_size = current_size

    with open(log_file) as f:
        lines = f.readlines()

    # Parse recent entries
    for line in lines[-10:]:  # Last 10 lines
        if 'Iter:' in line and 'Coherence:' in line:
            try:
                parts = line.split('|')
                iter_part = [p for p in parts if 'Iter:' in p][0]
                coh_part = [p for p in parts if 'Coherence:' in p][0]

                cycles = int(iter_part.split(':')[1].strip().replace(',', ''))
                coherence = float(coh_part.split(':')[1].strip())
                coherence_values.append(coherence)
            except:
                pass

    return {'cycles': cycles, 'coherence_values': coherence_values[-100:]}

def print_analysis(state):
    """Print current analysis."""
    if not state:
        return

    now = datetime.now().strftime('%H:%M:%S')
    elapsed = (time.time() - start_time) / 60

    print(f"\n[{now}] ANALYSIS:")
    print(f"  Total cycles: {state['cycles']:,}")
    print(f"  Elapsed: {elapsed:.1f} minutes")

    if state['coherence_values']:
        recent = state['coherence_values'][-10:]
        avg_coh = sum(recent) / len(recent)
        var_coh = sum((x - avg_coh)**2 for x in recent) / len(recent)

        print(f"  Recent coherence: {avg_coh:.6f} (var: {var_coh:.2e})")

        # Analysis
        if avg_coh < 0.01:
            print("  → System at HIHO attractor (optimal)")
        elif var_coh < 1e-8:
            print("  → Stable convergence achieved")
        else:
            print("  → Still exploring phase space")

    # Rate calculation
    rate = state['cycles'] / max(elapsed, 0.1)
    print(f"  Cycle rate: {rate:,.0f} cycles/min")

# Monitor loop
print("Monitoring... (Ctrl+C to stop)")
try:
    while True:
        state = analyze_state()
        if state:
            print_analysis(state)
        time.sleep(30)

except KeyboardInterrupt:
    print("\n\nMonitoring stopped")

    # Final analysis
    if os.path.exists(results_file):
        with open(results_file) as f:
            results = json.load(f)
        print("\nFinal Results:")
        print(f"  Duration: {results.get('duration_min', 0):.1f} min")
        print(f"  Total iterations: {results.get('iterations', 0):,}")
        print(f"  Target reached: {results.get('target_reached', False)}")
