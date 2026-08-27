#!/usr/bin/env python3
import time
from cohezion.reliability.system_wide_fleet_lock import SystemWideFleetLock

lock = SystemWideFleetLock("test_resource")
print("Acquiring lock...")
with lock.hold(timeout=5.0) as ok:
    if ok:
        print("✓ Successfully acquired cross-session SystemWideFleetLock!")
    else:
        print("✗ Failed to acquire lock")

print("Released lock cleanly.")
