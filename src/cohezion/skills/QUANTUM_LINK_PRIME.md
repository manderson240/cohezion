---
name: quantum-link-prime
description: "High-Performance Inter-Process Communication (IPC) for Distributed Agent Swarms. Expertise in replacing slow Database Polling (10-100ms) with Shared Memory (0.02ms) using Linux /dev/shm."
metadata:
  version: "v1.0 (Extracted Phase 56)"
  concepts: ["Shared Memory", "File Locking (`fcntl`)", "RAM Disk", "JSON State"]
  source: "src/cohezion/skills/QUANTUM_LINK_PRIME.md"
---

# SKILL: QUANTUM_LINK_PRIME

## DOMAIN EXPERTISE
**High-Performance Inter-Process Communication (IPC)** for Distributed Agent Swarms.
Expertise in replacing slow Database Polling (10-100ms) with **Shared Memory (0.02ms)** using Linux `/dev/shm`.

## KEY TEXTS & CONCEPTS
*   **Shared Memory**: Using RAM buffers mapped to file descriptors for zero-copy data sharing.
*   **File Locking (`fcntl`)**: Critical for preventing race conditions (Read-Modify-Write cycles).
*   **RAM Disk**: `/dev/shm` on Linux is a tmpfs backed by RAM. Writing to it is instantaneous.
*   **JSON State**: Simple key-value store suitable for configuration, flags, and telemetry.

## INSTRUCTION

### 1. The Mechanic
Use `QUANTUM_LINK` when agents need to share state *faster* than the database allows (e.g., "Stop Button", "Real-time Chaos", "Audio Sync").

### 2. Implementation Template (`quantum_link.py`)
```python
import json
import fcntl
import time
from pathlib import Path

QUANTUM_PATH = Path("/dev/shm/cohezion_quantum_state.json")

def update_quantum_state(**kwargs):
    # R-M-W Cycle with Lock
    with open(QUANTUM_PATH, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX) # Exclusive Lock
        try:
            data = json.load(f)
        except:
            data = {}
        data.update(kwargs)
        f.seek(0)
        json.dump(data, f)
        f.truncate()
        fcntl.flock(f, fcntl.LOCK_UN) # Release

def read_quantum_state():
    with open(QUANTUM_PATH, 'r') as f:
        fcntl.flock(f, fcntl.LOCK_SH) # Shared Lock
        return json.load(f)
```

## VERSION
v1.0 (Extracted Phase 56)

## SEE ALSO
*   `src/cohezion/core/quantum_link.py` (Reference Implementation)
*   `RETROSPECTIVE_PHASE_50_59_SINGULARITY.md`
