import datetime
import os
import time
from enum import Enum
from pathlib import Path

import psutil


# Cohezion Resource Guard (Quadrature Nexus Stability)
# Hardware Profile: 128GB RAM, AMD Ryzen 9 (32 threads)
MEM_WARN_PERCENT = 85
MEM_CRIT_PERCENT = 95
CPU_LOAD_WARN = 45.0  # 32 Threads, so 45 is high utilization queue
CPU_LOAD_CRIT = 60.0

LOCK_FILE = Path("/tmp/cohezion_pressure.lock")
LOG_FILE = Path("logs/system_monitor.log")


class AlertLevel(Enum):
    GREEN = 0
    YELLOW = 1
    RED = 2


def log(msg):
    timestamp = datetime.datetime.now().isoformat()
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")


def set_pressure_signal(level: AlertLevel):
    if level == AlertLevel.GREEN:
        if LOCK_FILE.exists():
            log("State GREEN: Releasing pressure lock.")
            LOCK_FILE.unlink()
    else:
        if not LOCK_FILE.exists():
            with open(LOCK_FILE, "w") as f:
                f.write(f"LEVEL={level.name}\nPID={os.getpid()}")
            log(f"State {level.name}: Pressure lock engaged.")


def monitor():
    log(f"--- Cohezion Active Defense Started (PID: {os.getpid()}) ---")
    log(f"Thresholds: Mem > {MEM_WARN_PERCENT}% | Load > {CPU_LOAD_WARN}")

    # Ensure log dir exists
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            mem = psutil.virtual_memory()
            load = os.getloadavg()[0]  # 1 min load avg

            level = AlertLevel.GREEN
            msg_parts = []

            # Memory Logic
            if mem.percent > MEM_CRIT_PERCENT:
                level = AlertLevel.RED
                msg_parts.append(f"MEM_CRIT({mem.percent}%)")
            elif mem.percent > MEM_WARN_PERCENT:
                level = max(level, AlertLevel.YELLOW)
                msg_parts.append(f"MEM_WARN({mem.percent}%)")

            # CPU Logic
            if load > CPU_LOAD_CRIT:
                level = AlertLevel.RED
                msg_parts.append(f"CPU_CRIT({load:.2f})")
            elif load > CPU_LOAD_WARN:
                level = max(level, AlertLevel.YELLOW)
                msg_parts.append(f"CPU_WARN({load:.2f})")

            # Actuation
            if level != AlertLevel.GREEN:
                set_pressure_signal(level)
                log(f"PRESSURE ALERT: {', '.join(msg_parts)}")

                if level == AlertLevel.RED:
                    # In a real scenario, we might kill non-essential PIDs here
                    # For now, just aggressive signaling
                    pass
            else:
                set_pressure_signal(AlertLevel.GREEN)

            time.sleep(5)
    except KeyboardInterrupt:
        log("Monitor stopping.")
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()


if __name__ == "__main__":
    monitor()
