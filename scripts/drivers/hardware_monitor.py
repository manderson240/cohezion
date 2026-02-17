#!/usr/bin/env python3
"""
Cohezion Hardware Electricity Tracker
Logs hardware power draw for R&D tax credit (Section 41/174A) documentation.
Estimates kWh based on TDP and dynamic load.
"""

import json
import os
import time
from datetime import datetime

import psutil


# CONFIGURATION: Adjust these to your specific rig
CPU_TDP_WATTS = 65  # Framework 16 Ryzen 9 7945HX Typical
GPU_TDP_WATTS = 120  # Radeon RX 7700S Max (Adjust if using external)
IDLE_BASE_WATTS = 20
LOG_FILE = "/home/mike-anderson/dev/cohezion/knowledge_graph/HARDWARE_LOG.jsonl"


def get_gpu_load():
    """Mock for systems without nvidia-smi/rocm-smi; can be extended."""
    # For AMD on Linux, we could parse /sys/class/drm/card0/device/gpu_busy_percent
    try:
        with open("/sys/class/drm/card0/device/gpu_busy_percent") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def calculate_power():
    cpu_load = psutil.cpu_percent(interval=1) / 100.0
    gpu_load = get_gpu_load() / 100.0

    cpu_watts = IDLE_BASE_WATTS + (CPU_TDP_WATTS * cpu_load)
    gpu_watts = GPU_TDP_WATTS * gpu_load

    total_watts = cpu_watts + gpu_watts
    return total_watts


def log_session():
    print(f"[*] Cohezion Hardware Tracker Active. Logging to {LOG_FILE}")
    try:
        while True:
            watts = calculate_power()
            timestamp = datetime.now().isoformat()

            entry = {
                "timestamp": timestamp,
                "watts": round(watts, 2),
                "kwh_instant": round(watts / 1000, 4),
            }

            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")

            # Print status every 5 mins or so to console
            # print(f"[{timestamp}] Power Draw: {watts:.2f}W")

            time.sleep(60)  # Log every minute
    except KeyboardInterrupt:
        print("\n[*] Logging stopped.")


if __name__ == "__main__":
    # Ensure directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log_session()
