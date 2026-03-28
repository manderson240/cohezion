#!/usr/bin/env python3
"""Check Ralph Loop status and report progress."""

import glob
import json
import re
from pathlib import Path
from datetime import datetime

VAULT_BASE = Path.home() / "vaults" / "cohezion-vault" / "luma-speedrun" / "autoresearch"

def get_latest_log():
    """Find the most recent Ralph Loop log file."""
    logs = glob.glob(str(Path.home() / "ralph_loop_*.log"))
    if not logs:
        return None
    return max(logs, key=lambda x: Path(x).stat().st_mtime)

def parse_log(log_file):
    """Parse Ralph Loop log for status."""
    content = Path(log_file).read_text()

    # Find current kernel and cycle
    current_cycle = None
    current_kernel = None
    best_us = float('inf')
    coherence = 0.0

    # Extract kernel from "# KERNEL: xxx" lines
    kernel_matches = re.findall(r'# KERNEL: (\w+)', content)
    if kernel_matches:
        current_kernel = kernel_matches[-1]

    # Extract cycle info
    cycle_matches = re.findall(r'Cycle (\d+)/(\d+)', content)
    if cycle_matches:
        current_cycle = int(cycle_matches[-1][0])
        total_cycles = int(cycle_matches[-1][1])
    else:
        total_cycles = 75

    # Extract best result
    best_matches = re.findall(r'New best: ([\d.]+)µs', content)
    if best_matches:
        best_us = float(best_matches[-1])

    # Extract coherence
    coherence_matches = re.findall(r'coherence=([\d.]+)', content)
    if coherence_matches:
        coherence = float(coherence_matches[-1])

    # Check for breakthrough
    breakthrough = "BREAKTHROUGH" in content

    return {
        'kernel': current_kernel,
        'cycle': current_cycle,
        'total_cycles': total_cycles,
        'best_us': best_us,
        'coherence': coherence,
        'breakthrough': breakthrough,
        'log_file': log_file,
    }

def check_vault_state(kernel):
    """Check vault state for a kernel."""
    state_file = VAULT_BASE / kernel / "state.json"
    if state_file.exists():
        return json.loads(state_file.read_text())
    return None

def main():
    log_file = get_latest_log()
    if not log_file:
        print("No Ralph Loop log file found")
        return

    status = parse_log(log_file)
    print(f"Ralph Loop Status ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print("=" * 60)
    print(f"Kernel: {status['kernel']}")
    print(f"Cycle: {status['cycle']}/{status['total_cycles']}")
    print(f"Best: {status['best_us']:.1f}µs")
    print(f"Coherence: {status['coherence']:.3f}")
    print(f"Breakthrough: {'YES!' if status['breakthrough'] else 'No'}")
    print(f"Log: {status['log_file']}")

    if status['kernel']:
        vault_state = check_vault_state(status['kernel'])
        if vault_state:
            print(f"\nVault State ({status['kernel']}):")
            print(f"  Best: {vault_state.get('best_us', 'N/A')}")
            print(f"  Total Cycles: {vault_state.get('total_cycles', 'N/A')}")
            print(f"  Stagnation: {vault_state.get('stagnation_count', 'N/A')}")

if __name__ == "__main__":
    main()
